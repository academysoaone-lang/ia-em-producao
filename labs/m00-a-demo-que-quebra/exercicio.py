"""Módulo 0 · Expectativa vs. realidade de produção

Dois exercícios curtos para fixar o mapa do sistema que o curso inteiro vai construir:

    entrada  ->  orquestrador (RAG, memória, ferramentas)  ->  modelo  ->  saída

Rode `python labs/m00-a-demo-que-quebra/demo.py` antes de começar.
Teste com: pytest labs/m00-a-demo-que-quebra
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Callable

from soaone_lab import LLM, Mensagem

CAMADAS = ("entrada", "orquestrador", "modelo", "saida")

SINTOMAS = {
    # TODO 1: para cada sintoma, escreva a camada que deveria evitá-lo:
    # "entrada", "orquestrador", "modelo" ou "saida".
    "esquece o que o usuário disse duas mensagens atrás": "",
    "inventa a política de reembolso": "",
    "obedece a 'ignore as instruções anteriores'": "",
    "responde perguntas fora do negócio": "",
    "mostra um preço diferente do catálogo": "",
    "envia link para um domínio desconhecido": "",
    "cpf do cliente aparece no log do provedor": "",
    "resposta muda de estilo entre versões do modelo": "",
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
        """TODO 2: implemente o caminho completo de uma mensagem.

        1. Passe o texto por cada filtro de `entrada`, em ordem (cada um pode alterar o texto).
        2. Chame o `orquestrador` para montar as mensagens.
        3. Chame `self.llm.chat(mensagens)` e pegue `.texto`.
        4. Passe a resposta por cada filtro de `saida`, em ordem.
        Ao fim de cada etapa, adicione ao `registro`: "entrada ok", "orquestrador ok", "modelo ok", "saida ok".
        Se qualquer filtro levantar `Bloqueado`, registre f"bloqueado em {etapa}: {motivo}"
        e devolva `self.resposta_bloqueio` sem chamar as etapas seguintes.
        """
        raise NotImplementedError("TODO 2: Pipeline.processar")
