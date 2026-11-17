"""Módulo 2 · Do chatbot ao agente · Exercício

  1. validar os argumentos que o modelo pede, contra o JSON Schema da ferramenta (aula 2.1);
  2. o loop do agente com limite de passos e identidade vinda da sessão (aula 2.2);
  3. saída estruturada validada com Pydantic, com nova tentativa (aula 2.3);
  4. streaming com ponto de corte para a validação de saída (aula 2.4).

Teste com: pytest labs/m02-do-chatbot-ao-agente
"""
from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from typing import Any, Callable, Iterable, Iterator, Literal

from pydantic import BaseModel, Field, ValidationError

from soaone_lab import LLM, ChamadaFerramenta, Mensagem


# ---------------------------------------------------------------- Aula 2.1 · tool calling
class ArgumentosInvalidos(ValueError):
    pass


TIPOS = {"string": str, "integer": int, "number": (int, float), "boolean": bool, "object": dict, "array": list}


def validar_argumentos(schema: dict, argumentos: dict) -> dict:
    """Valida `argumentos` contra um JSON Schema simples (type object) e devolve os argumentos."""
    # TODO 1: valide e levante ArgumentosInvalidos com uma mensagem clara quando:
    #   - faltar um campo de schema["required"];
    #   - vier um campo que não está em schema["properties"] (additionalProperties é sempre false aqui);
    #   - o tipo não bater com TIPOS[prop["type"]] (cuidado: bool é subclasse de int em Python!);
    #   - o valor não estiver em prop["enum"], quando existir;
    #   - um número sair de prop["minimum"] / prop["maximum"], quando existirem.
    #   Se estiver tudo certo, devolva os argumentos.
    raise NotImplementedError("TODO 1")


@dataclass
class Ferramenta:
    nome: str
    descricao: str
    parametros: dict                      # JSON Schema dos argumentos que o MODELO preenche
    funcao: Callable[..., Any]
    usa_cliente_da_sessao: bool = False   # se True, o código injeta cliente_id da sessão

    def para_provedor(self) -> dict:
        return {"name": self.nome, "description": self.descricao, "parameters": self.parametros}


# ---------------------------------------------------------------- Aula 2.2 · o loop do agente
class LimiteDePassos(RuntimeError):
    pass


@dataclass
class Sessao:
    cliente_id: str
    passos: list[str] = field(default_factory=list)


def executar_agente(llm: LLM, pergunta: str, ferramentas: list[Ferramenta], sessao: Sessao,
                    sistema: str = "Você é o atendente da Loja soaone.", max_passos: int = 5) -> str:
    """Pensar, agir, observar, até o modelo devolver texto sem pedir ferramenta."""
    # TODO 2: implemente o loop.
    #   - mensagens começa com [system, user]; envie as ferramentas com f.para_provedor().
    #   - Se a resposta não pedir ferramentas, devolva resposta.texto.
    #   - Para cada ChamadaFerramenta pedida:
    #   * ferramenta desconhecida -> resultado {"erro": "ferramenta desconhecida"};
    #   * valide os argumentos com validar_argumentos (erro vira {"erro": str(e)}, devolvido ao modelo);
    #   * se f.usa_cliente_da_sessao, passe cliente_id=sessao.cliente_id. NUNCA aceite um cliente_id
    #   vindo do modelo: o schema nem deve tê-lo, e se vier, a validação recusa;
    #   * registre f"{nome}({argumentos})" em sessao.passos;
    #   * acrescente às mensagens um {"role": "assistant", "content": "", "tool_call": nome}
    #   e um {"role": "tool", "name": nome, "content": json.dumps(resultado, ensure_ascii=False)}.
    #   - Ao passar de max_passos chamadas ao modelo sem resposta final, levante LimiteDePassos.
    raise NotImplementedError("TODO 2")


# ---------------------------------------------------------------- Aula 2.3 · structured output
class Ticket(BaseModel):
    categoria: Literal["entrega", "reembolso", "defeito", "cadastro", "outro"]
    prioridade: int = Field(ge=1, le=5)
    resumo: str = Field(min_length=5, max_length=200)
    pedido: str | None = Field(default=None, pattern=r"^\d{6}$")


class SaidaInvalida(ValueError):
    pass


def extrair_json(texto: str) -> Any:
    """Tira cercas ```json ... ``` e texto em volta, e faz o parse do primeiro objeto JSON."""
    # TODO 3a: modelos adoram embrulhar o JSON em ```json ... ``` ou em "Aqui está: {...}".
    #   Encontre o primeiro '{' e o último '}' e faça json.loads do trecho. Sem objeto, levante SaidaInvalida.
    raise NotImplementedError("TODO 3a")


def extrair_ticket(llm: LLM, mensagem_cliente: str, tentativas: int = 2) -> Ticket:
    """Pede ao modelo um Ticket em JSON e só devolve se passar na validação do Pydantic."""
    mensagens: list[Mensagem] = [
        {"role": "system", "content": "Classifique a mensagem do cliente. Responda só com JSON no schema: "
                                      + json.dumps(Ticket.model_json_schema(), ensure_ascii=False)},
        {"role": "user", "content": mensagem_cliente},
    ]
    # TODO 3b: chame o modelo, use extrair_json e Ticket.model_validate.
    #   Se falhar (SaidaInvalida ou ValidationError), acrescente a resposta do modelo e uma mensagem
    #   de usuário com o erro ("Sua resposta não passou na validação: ...") e tente de novo.
    #   Depois de `tentativas` falhas, levante SaidaInvalida.
    raise NotImplementedError("TODO 3b")


# ---------------------------------------------------------------- Aula 2.4 · streaming
def stream_validado(fragmentos: Iterable[str], validar: Callable[[str], bool],
                    substituto: str = " [resposta interrompida pela validação]") -> Iterator[str]:
    """Repassa o streaming frase a frase, validando cada frase antes de mostrar ao usuário."""
    # TODO 4: o ponto de corte é a FRASE. Acumule fragmentos num buffer; sempre que o buffer
    #   tiver uma frase completa (termina em . ! ? seguido de espaço, ou o fim do stream),
    #   valide a frase com `validar`. Se passar, entregue (yield) a frase. Se não passar,
    #   entregue `substituto` e PARE: nada depois dela pode sair.
    #   No fim do stream, valide e entregue o que sobrou no buffer (se houver).
    raise NotImplementedError("TODO 4")
