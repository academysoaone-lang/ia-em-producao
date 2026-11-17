"""Módulo 0 · Solução de referência."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Callable

from soaone_lab import LLM, Mensagem

CAMADAS = ("entrada", "orquestrador", "modelo", "saida")

SINTOMAS = {
    "esquece o que o usuário disse duas mensagens atrás": "orquestrador",
    "inventa a política de reembolso": "orquestrador",
    "obedece a 'ignore as instruções anteriores'": "entrada",
    "responde perguntas fora do negócio": "entrada",
    "mostra um preço diferente do catálogo": "saida",
    "envia link para um domínio desconhecido": "saida",
    "cpf do cliente aparece no log do provedor": "entrada",
    "resposta muda de estilo entre versões do modelo": "modelo",
}


def camada_do_sintoma(sintoma: str) -> str:
    """Devolve a camada do sistema responsável por evitar o sintoma."""
    return SINTOMAS[sintoma]


class Bloqueado(Exception):
    def __init__(self, etapa: str, motivo: str):
        super().__init__(f"{etapa}: {motivo}")
        self.etapa, self.motivo = etapa, motivo


Filtro = Callable[[str], str]                       # recebe texto, devolve texto (talvez alterado) ou levanta Bloqueado
Orquestrador = Callable[[str], list[Mensagem]]      # monta as mensagens que vão para o modelo


@dataclass
class Pipeline:
    llm: LLM
    orquestrador: Orquestrador
    entrada: list[Filtro] = field(default_factory=list)
    saida: list[Filtro] = field(default_factory=list)
    resposta_bloqueio: str = "Não posso ajudar com isso por aqui."
    registro: list[str] = field(default_factory=list)

    def processar(self, mensagem: str) -> str:
        try:
            texto = mensagem
            for f in self.entrada:
                texto = f(texto)
            self.registro.append("entrada ok")
            mensagens = self.orquestrador(texto)
            self.registro.append("orquestrador ok")
            resposta = self.llm.chat(mensagens).texto
            self.registro.append("modelo ok")
            for f in self.saida:
                resposta = f(resposta)
            self.registro.append("saida ok")
            return resposta
        except Bloqueado as b:
            self.registro.append(f"bloqueado em {b.etapa}: {b.motivo}")
            return self.resposta_bloqueio
