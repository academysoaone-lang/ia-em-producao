"""Módulo 3 · Production readiness · Solução de referência

  1. prompt organizado para o cache: estático no começo, variável no fim (aula 3.1);
  2. retry com backoff e troca de provedor (aula 3.2);
  3. um executor de evals que barra o deploy (aula 3.3);
  4. trace por passo com tokens, custo, duração e erro (aula 3.4).

Teste com: pytest labs/m03-production-readiness
"""
from __future__ import annotations

import json
import re
import time
import uuid
from contextlib import contextmanager
from dataclasses import asdict, dataclass, field
from datetime import datetime
from typing import Callable, Iterator

from soaone_lab import LLM, ErroProvedor, Mensagem, Resposta, custo_usd


# ---------------------------------------------------------------- Aula 3.1 · prompt caching
def montar_prompt(sistema: str, regras: list[str], exemplos: list[tuple[str, str]],
                  historico: list[Mensagem], pergunta: str, agora: datetime) -> list[Mensagem]:
    """Monta as mensagens pensando no cache de prompt do provedor."""
    partes = [sistema, "Regras:\n" + "\n".join(f"- {r}" for r in regras)]
    if exemplos:
        partes.append("Exemplos:\n" + "\n\n".join(f"Cliente: {c}\nAtendente: {a}" for c, a in exemplos))
    return ([{"role": "system", "content": "\n\n".join(partes)}] + list(historico)
            + [{"role": "user", "content": f"[{agora:%d/%m/%Y %H:%M}] {pergunta}"}])


def prefixo_comum(a: list[Mensagem], b: list[Mensagem]) -> int:
    """Quantos caracteres do início das duas conversas são idênticos (o que o cache aproveitaria)."""
    sa = "".join(f"{m['role']}:{m['content']}|" for m in a)
    sb = "".join(f"{m['role']}:{m['content']}|" for m in b)
    n = 0
    for x, y in zip(sa, sb):
        if x != y:
            break
        n += 1
    return n


# ---------------------------------------------------------------- Aula 3.2 · fallback
class TodosProvedoresFalharam(RuntimeError):
    pass


@dataclass
class ClienteComFallback:
    provedores: list[LLM]
    tentativas_por_provedor: int = 3
    espera_base: float = 0.5
    dormir: Callable[[float], None] = time.sleep
    log: list[str] = field(default_factory=list)

    @property
    def nome(self) -> str:
        return "+".join(p.nome for p in self.provedores)

    def chat(self, mensagens: list[Mensagem], ferramentas: list[dict] | None = None) -> Resposta:
        for p in self.provedores:
            for n in range(self.tentativas_por_provedor):
                try:
                    r = p.chat(mensagens, ferramentas)
                    self.log.append(f"{p.nome}:ok")
                    return r
                except ErroProvedor:
                    self.log.append(f"{p.nome}:erro")
                    if n < self.tentativas_por_provedor - 1:
                        self.dormir(self.espera_base * 2 ** n)
        raise TodosProvedoresFalharam(" / ".join(self.log))


# ---------------------------------------------------------------- Aula 3.3 · evals
@dataclass
class Relatorio:
    total: int = 0
    aprovados: int = 0
    falhas: list[tuple[str, str]] = field(default_factory=list)   # (id do caso, motivo)

    @property
    def taxa(self) -> float:
        return self.aprovados / self.total if self.total else 0.0

    def aprovado(self, minimo: float = 0.9, sem_falha_em: tuple[str, ...] = ("seguranca",)) -> bool:
        """O deploy só passa com a taxa mínima E nenhuma falha nas categorias críticas."""
        criticas = [f for f in self.falhas if f[0].split("-")[0] in sem_falha_em]
        return self.taxa >= minimo and not criticas


def carregar_casos(caminho: str) -> list[dict]:
    with open(caminho, encoding="utf-8") as f:
        return [json.loads(l) for l in f if l.strip() and not l.startswith("//")]


def julgar(juiz: LLM, pergunta: str, resposta: str, criterio: str) -> bool:
    """LLM como juiz: devolve True se o juiz responder APROVADO."""
    r = juiz.chat([
        {"role": "system", "content": "Você avalia respostas de um atendente. Responda só APROVADO ou REPROVADO."},
        {"role": "user", "content": f"Critério: {criterio}\nPergunta: {pergunta}\nResposta: {resposta}"},
    ]).texto
    return r.strip().upper().startswith("APROVADO")


def rodar_evals(sistema: Callable[[str], str], casos: list[dict], juiz: LLM | None = None) -> Relatorio:
    """Roda cada caso contra o sistema e devolve o relatório."""
    rel = Relatorio()
    for c in casos:
        rel.total += 1
        try:
            resp = sistema(c["entrada"])
        except Exception as e:  # noqa: BLE001 - o eval registra qualquer quebra
            rel.falhas.append((c["id"], f"exceção: {e}"))
            continue
        t, esp, baixa = c["tipo"], c["esperado"], resp.lower()
        if t == "contem":
            ok, motivo = esp.lower() in baixa, f"não contém {esp!r}"
        elif t == "nao_contem":
            achou = [x for x in esp if x.lower() in baixa]
            ok, motivo = not achou, f"contém proibido {achou}"
        elif t == "regex":
            ok, motivo = bool(re.search(esp, resp, re.I)), f"não casa com /{esp}/"
        elif t == "juiz":
            ok, motivo = (juiz is not None and julgar(juiz, c["entrada"], resp, esp)), f"juiz reprovou: {esp}"
        else:
            ok, motivo = False, f"tipo desconhecido: {t}"
        if ok:
            rel.aprovados += 1
        else:
            rel.falhas.append((c["id"], motivo))
    return rel


# ---------------------------------------------------------------- Aula 3.4 · observabilidade
@dataclass
class Passo:
    nome: str
    dados: dict = field(default_factory=dict)
    tokens_entrada: int = 0
    tokens_saida: int = 0
    custo_usd: float = 0.0
    duracao_ms: float = 0.0
    erro: str | None = None


class Tracer:
    def __init__(self, relogio: Callable[[], float] = time.perf_counter):
        self.relogio = relogio
        self.traces: dict[str, list[Passo]] = {}

    def iniciar(self) -> str:
        tid = uuid.uuid4().hex[:12]
        self.traces[tid] = []
        return tid

    @contextmanager
    def passo(self, trace_id: str, nome: str, **dados) -> Iterator[Passo]:
        p = Passo(nome, dados)
        self.traces[trace_id].append(p)
        inicio = self.relogio()
        try:
            yield p
        except Exception as e:
            p.erro = f"{type(e).__name__}: {e}"
            raise
        finally:
            p.duracao_ms = round((self.relogio() - inicio) * 1000, 2)

    @staticmethod
    def registrar_llm(passo: Passo, resposta: Resposta, tabela_preco: str = "falso") -> None:
        passo.tokens_entrada = resposta.uso.entrada
        passo.tokens_saida = resposta.uso.saida
        passo.custo_usd = custo_usd(resposta.uso.entrada, resposta.uso.saida, tabela_preco, resposta.uso.entrada_cache)

    def resumo(self, trace_id: str) -> dict:
        ps = self.traces[trace_id]
        return {
            "passos": [p.nome for p in ps],
            "tokens": sum(p.tokens_entrada + p.tokens_saida for p in ps),
            "custo_usd": round(sum(p.custo_usd for p in ps), 6),
            "duracao_ms": round(sum(p.duracao_ms for p in ps), 2),
            "erros": [p.erro for p in ps if p.erro],
        }

    def exportar_jsonl(self, caminho: str) -> None:
        with open(caminho, "w", encoding="utf-8") as f:
            for tid, ps in self.traces.items():
                for p in ps:
                    f.write(json.dumps({"trace": tid, **asdict(p)}, ensure_ascii=False) + "\n")
