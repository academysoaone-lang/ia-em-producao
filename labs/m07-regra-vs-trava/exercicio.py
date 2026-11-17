"""Módulo 7 · Regra vs. trava · Exercício

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
    # TODO 1: devolva [system, user]:
    #   - system: `sistema` + "\n\nRegras:\n" + regras (uma por linha, com "- ");
    #   - user: os documentos (separados por linha em branco), depois a pergunta como
    #   "Pergunta: ...", e por ÚLTIMO "Lembre-se: " + as regras juntadas com "; ".
    #   Isto ajuda, mas continua sendo um PEDIDO: o resto do lab é sobre o que não pode depender dele.
    raise NotImplementedError("TODO 1")


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
        # TODO 2: decida, nesta ordem (a primeira regra que se aplica vence):
        #   1. ferramenta não cadastrada           -> negar, "ferramenta desconhecida"
        #   2. ctx.papel fora de regra.papeis      -> negar, "papel sem permissão"
        #   3. so_desenvolvimento em producao      -> negar, "bloqueada em produção"
        #   4. risco "irreversivel"                -> aprovar, "ação irreversível"
        #   5. limite_valor e argumentos["valor"] > limite -> aprovar, "valor acima do limite"
        #   6. senão                               -> permitir, "ok"
        #   O modelo nunca escolhe o papel nem o ambiente: eles vêm do Contexto, que vem da sessão.
        raise NotImplementedError("TODO 2")


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
        # TODO 3a: só decide pedido "pendente". O aprovador precisa ter papel em
        #   papeis_aprovadores e NÃO pode ser o próprio solicitante (quatro olhos).
        #   Qualquer violação -> AprovacaoNegada. Marque status e aprovador.
        raise NotImplementedError("TODO 3a")

    def executar(self, pedido_id: int, executor) -> object:
        # TODO 3b: só executa pedido "aprovado", uma única vez. Chame
        #   executor(**argumentos), marque "executado" e devolva o resultado.
        #   Qualquer outro status -> AprovacaoNegada.
        raise NotImplementedError("TODO 3b")


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
    # TODO 4: normalize espaços e minúsculas. Depois:
    #   - em "producao", só passam comandos de SOMENTE_LEITURA (lista branca); o resto é bloqueado;
    #   - em qualquer ambiente, um padrão de DESTRUTIVOS bloqueia;
    #   - comandos encadeados (&&, ;, ||, |) são verificados parte por parte.
    #   Bloqueio -> ComandoBloqueado com o comando no motivo.
    raise NotImplementedError("TODO 4")
