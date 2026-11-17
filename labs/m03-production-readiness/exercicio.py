"""Módulo 3 · Production readiness · Exercício

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
    # TODO 1: o cache do provedor reaproveita o MAIOR PREFIXO idêntico entre chamadas.
    #   - A primeira mensagem (system) deve ter SÓ conteúdo estático, nesta ordem:
    #   o texto de `sistema`, as `regras` (uma por linha, com "- ") e os `exemplos`
    #   no formato "Cliente: ...\nAtendente: ...".
    #   - Depois vem o `historico`, como está.
    #   - Por último, a mensagem do usuário com a data/hora e a pergunta:
    #   f"[{agora:%d/%m/%Y %H:%M}] {pergunta}".
    #   Um timestamp no topo do system invalidaria o cache inteiro a cada minuto.
    raise NotImplementedError("TODO 1")


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
        # TODO 2: para cada provedor, em ordem, tente até `tentativas_por_provedor` vezes.
        #   - Sucesso: registre f"{provedor.nome}:ok" no log e devolva a resposta.
        #   - ErroProvedor: registre f"{provedor.nome}:erro" e, se ainda houver tentativa
        #   nesse provedor, espere espera_base * 2**n (n = 0, 1, 2...) chamando self.dormir.
        #   Não espere depois da última tentativa: passe direto para o próximo provedor.
        #   - Outros erros (bug no seu código) NÃO devem ser engolidos.
        #   Se todos falharem, levante TodosProvedoresFalharam.
        raise NotImplementedError("TODO 2")


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
    # TODO 3: para cada caso, chame sistema(caso["entrada"]) e confira conforme caso["tipo"]:
    #   "contem"     -> caso["esperado"] aparece na resposta (sem diferenciar maiúsculas);
    #   "nao_contem" -> NENHUM item de caso["esperado"] (lista) aparece na resposta;
    #   "regex"      -> re.search(caso["esperado"], resposta, re.I);
    #   "juiz"       -> julgar(juiz, entrada, resposta, caso["esperado"]); sem juiz, conta como falha.
    #   Se o sistema levantar exceção, o caso falha com o motivo "exceção: ...".
    #   Falha vai para relatorio.falhas como (caso["id"], motivo).
    raise NotImplementedError("TODO 3")


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
        # TODO 4a: crie o Passo, adicione ao trace, entregue (yield) o passo para quem chamou.
        #   Ao sair do bloco, preencha duracao_ms (use self.relogio(), em milissegundos).
        #   Se o bloco levantar exceção, registre passo.erro = f"{Tipo}: mensagem" e
        #   RELANCE a exceção: o trace observa, não engole erro.
        raise NotImplementedError("TODO 4a")

    @staticmethod
    def registrar_llm(passo: Passo, resposta: Resposta, tabela_preco: str = "falso") -> None:
        passo.tokens_entrada = resposta.uso.entrada
        passo.tokens_saida = resposta.uso.saida
        passo.custo_usd = custo_usd(resposta.uso.entrada, resposta.uso.saida, tabela_preco, resposta.uso.entrada_cache)

    def resumo(self, trace_id: str) -> dict:
        # TODO 4b: devolva {"passos": [nomes], "tokens": total entrada+saída,
        #   "custo_usd": soma arredondada em 6 casas, "duracao_ms": soma, "erros": [passo.erro não nulos]}.
        raise NotImplementedError("TODO 4b")

    def exportar_jsonl(self, caminho: str) -> None:
        with open(caminho, "w", encoding="utf-8") as f:
            for tid, ps in self.traces.items():
                for p in ps:
                    f.write(json.dumps({"trace": tid, **asdict(p)}, ensure_ascii=False) + "\n")
