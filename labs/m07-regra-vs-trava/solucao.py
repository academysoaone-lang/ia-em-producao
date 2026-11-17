"""Módulo 7 · Regra vs. trava · Solução de referência

Regras no texto servem para estilo e formato. Permissão, dinheiro e ações irreversíveis
precisam de travas em código, que funcionam mesmo quando o modelo "esquece" a regra.
  1. reforço da regra perto da pergunta, contra a degradação da atenção (aula 7.1);
  2. política de ferramentas: menor privilégio decidido pelo código (aula 7.2);
  3. aprovação humana para o que é irreversível (aula 7.3);
  4. rede de segurança para agentes de código: comandos destrutivos bloqueados (aula 7.3).

Teste com: pytest labs/m07-regra-vs-trava
"""
from __future__ import annotations

import itertools
import re
from dataclasses import dataclass, field
from typing import Literal

from soaone_lab import Mensagem


# ---------------------------------------------------------------- Aula 7.1 · degradação da atenção
def montar_com_reforco(sistema: str, regras: list[str], documentos: list[str], pergunta: str) -> list[Mensagem]:
    """Modelos usam pior o que está no meio de contextos longos. Repita as regras no fim."""
    lista = "\n".join(f"- {r}" for r in regras)
    corpo = "\n\n".join(documentos) + f"\n\nPergunta: {pergunta}\n\nLembre-se: " + "; ".join(regras)
    return [{"role": "system", "content": f"{sistema}\n\nRegras:\n{lista}"},
            {"role": "user", "content": corpo.lstrip()}]


# ---------------------------------------------------------------- Aula 7.2 · política de ferramentas
Risco = Literal["leitura", "escrita", "irreversivel"]


@dataclass
class RegraFerramenta:
    nome: str
    risco: Risco
    papeis: set[str]                   # quem pode usar
    limite_valor: float | None = None  # acima disso, precisa de aprovação humana
    so_desenvolvimento: bool = False   # nunca roda em produção


@dataclass
class Contexto:
    usuario: str
    papel: str
    ambiente: Literal["desenvolvimento", "producao"] = "producao"


@dataclass
class Decisao:
    acao: Literal["permitir", "negar", "aprovar"]
    motivo: str


class PoliticaFerramentas:
    def __init__(self, regras: list[RegraFerramenta]):
        self.regras = {r.nome: r for r in regras}

    def autorizar(self, nome: str, argumentos: dict, ctx: Contexto) -> Decisao:
        r = self.regras.get(nome)
        if r is None:
            return Decisao("negar", "ferramenta desconhecida")
        if ctx.papel not in r.papeis:
            return Decisao("negar", "papel sem permissão")
        if r.so_desenvolvimento and ctx.ambiente == "producao":
            return Decisao("negar", "bloqueada em produção")
        if r.risco == "irreversivel":
            return Decisao("aprovar", "ação irreversível")
        if r.limite_valor is not None and float(argumentos.get("valor", 0)) > r.limite_valor:
            return Decisao("aprovar", "valor acima do limite")
        return Decisao("permitir", "ok")


# ---------------------------------------------------------------- Aula 7.3 · aprovação humana
class AprovacaoNegada(Exception):
    pass


@dataclass
class Pedido:
    id: int
    ferramenta: str
    argumentos: dict
    solicitante: str
    status: Literal["pendente", "aprovado", "rejeitado", "executado"] = "pendente"
    aprovador: str | None = None


@dataclass
class FilaAprovacao:
    papeis_aprovadores: set[str] = field(default_factory=lambda: {"supervisor"})
    pedidos: dict[int, Pedido] = field(default_factory=dict)
    _ids: itertools.count = field(default_factory=lambda: itertools.count(1))

    def solicitar(self, ferramenta: str, argumentos: dict, ctx: Contexto) -> int:
        p = Pedido(next(self._ids), ferramenta, dict(argumentos), ctx.usuario)
        self.pedidos[p.id] = p
        return p.id

    def decidir(self, pedido_id: int, aprovador: Contexto, aprovar: bool) -> Pedido:
        p = self.pedidos[pedido_id]
        if p.status != "pendente":
            raise AprovacaoNegada(f"pedido {pedido_id} já está {p.status}")
        if aprovador.papel not in self.papeis_aprovadores:
            raise AprovacaoNegada("papel sem permissão para aprovar")
        if aprovador.usuario == p.solicitante:
            raise AprovacaoNegada("quem pede não aprova")
        p.status = "aprovado" if aprovar else "rejeitado"
        p.aprovador = aprovador.usuario
        return p

    def executar(self, pedido_id: int, executor) -> object:
        p = self.pedidos[pedido_id]
        if p.status != "aprovado":
            raise AprovacaoNegada(f"pedido {pedido_id} está {p.status}")
        resultado = executor(**p.argumentos)
        p.status = "executado"
        return resultado


# ---------------------------------------------------------------- Aula 7.3 · rede de segurança
class ComandoBloqueado(Exception):
    pass


DESTRUTIVOS = [
    r"\bmigrate:(fresh|reset|refresh)\b", r"\bdb:(wipe|drop)\b", r"\bdrop\s+(database|schema|table)\b",
    r"\btruncate\s+(table\s+)?\w+", r"\bdelete\s+from\s+\w+\s*;?\s*$", r"\brm\s+-\w*r\w*f?\w*\s+(/|~|\*|\.)(\s|$)",
    r"\bgit\s+push\b.*(--force\b|\s-f\b)", r"\bgit\s+reset\s+--hard\b", r"\bterraform\s+destroy\b",
    r"\bkubectl\s+delete\s+(namespace|ns)\b", r"\bdocker\s+(system|volume)\s+prune\b",
]
SOMENTE_LEITURA = [r"^(ls|cat|head|tail|grep|wc|pwd|echo)\b", r"^git\s+(status|log|diff|show)\b",
                   r"^kubectl\s+(get|describe|logs)\b"]


def verificar_comando(comando: str, ambiente: Literal["desenvolvimento", "producao"]) -> str:
    """Trava para agentes que executam comandos. Devolve o comando se puder rodar."""
    for parte in re.split(r"&&|\|\||;|\|", comando):
        p = re.sub(r"\s+", " ", parte.strip().lower())
        if not p:
            continue
        if any(re.search(rx, p) for rx in DESTRUTIVOS):
            raise ComandoBloqueado(f"comando destrutivo: {parte.strip()}")
        if ambiente == "producao" and not any(re.search(rx, p) for rx in SOMENTE_LEITURA):
            raise ComandoBloqueado(f"em produção o agente só lê: {parte.strip()}")
    return comando
