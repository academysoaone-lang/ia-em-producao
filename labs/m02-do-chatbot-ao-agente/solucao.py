"""Módulo 2 · Do chatbot ao agente · Solução de referência

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
    props = schema.get("properties", {})
    for req in schema.get("required", []):
        if req not in argumentos:
            raise ArgumentosInvalidos(f"campo obrigatório ausente: {req}")
    for nome, valor in argumentos.items():
        if nome not in props:
            raise ArgumentosInvalidos(f"campo não permitido: {nome}")
        p = props[nome]
        tipo = TIPOS[p["type"]]
        if (isinstance(valor, bool) and p["type"] != "boolean") or not isinstance(valor, tipo):
            raise ArgumentosInvalidos(f"{nome}: esperado {p['type']}, veio {type(valor).__name__}")
        if "enum" in p and valor not in p["enum"]:
            raise ArgumentosInvalidos(f"{nome}: {valor!r} não está em {p['enum']}")
        if "minimum" in p and valor < p["minimum"]:
            raise ArgumentosInvalidos(f"{nome}: menor que {p['minimum']}")
        if "maximum" in p and valor > p["maximum"]:
            raise ArgumentosInvalidos(f"{nome}: maior que {p['maximum']}")
    return argumentos


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
    por_nome = {f.nome: f for f in ferramentas}
    mensagens: list[Mensagem] = [{"role": "system", "content": sistema}, {"role": "user", "content": pergunta}]
    for _ in range(max_passos):
        resposta = llm.chat(mensagens, [f.para_provedor() for f in ferramentas])
        if not resposta.ferramentas:
            return resposta.texto
        for chamada in resposta.ferramentas:
            f = por_nome.get(chamada.nome)
            if f is None:
                resultado: Any = {"erro": "ferramenta desconhecida"}
            else:
                try:
                    args = dict(validar_argumentos(f.parametros, chamada.argumentos))
                    if f.usa_cliente_da_sessao:
                        args["cliente_id"] = sessao.cliente_id
                    resultado = f.funcao(**args)
                except ArgumentosInvalidos as e:
                    resultado = {"erro": str(e)}
            sessao.passos.append(f"{chamada.nome}({chamada.argumentos})")
            mensagens.append({"role": "assistant", "content": "", "tool_call": chamada.nome})
            mensagens.append({"role": "tool", "name": chamada.nome,
                              "content": json.dumps(resultado, ensure_ascii=False)})
    raise LimiteDePassos(f"o agente passou de {max_passos} passos sem terminar")


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
    i, j = texto.find("{"), texto.rfind("}")
    if i < 0 or j < i:
        raise SaidaInvalida("nenhum objeto JSON na resposta")
    try:
        return json.loads(texto[i:j + 1])
    except json.JSONDecodeError as e:
        raise SaidaInvalida(f"JSON malformado: {e}") from e


def extrair_ticket(llm: LLM, mensagem_cliente: str, tentativas: int = 2) -> Ticket:
    """Pede ao modelo um Ticket em JSON e só devolve se passar na validação do Pydantic."""
    mensagens: list[Mensagem] = [
        {"role": "system", "content": "Classifique a mensagem do cliente. Responda só com JSON no schema: "
                                      + json.dumps(Ticket.model_json_schema(), ensure_ascii=False)},
        {"role": "user", "content": mensagem_cliente},
    ]
    for _ in range(tentativas):
        texto = llm.chat(mensagens).texto
        try:
            return Ticket.model_validate(extrair_json(texto))
        except (SaidaInvalida, ValidationError) as e:
            mensagens.append({"role": "assistant", "content": texto})
            mensagens.append({"role": "user", "content": f"Sua resposta não passou na validação: {e}. "
                                                         "Responda de novo, só com o JSON corrigido."})
    raise SaidaInvalida(f"o modelo não produziu um Ticket válido em {tentativas} tentativas")


# ---------------------------------------------------------------- Aula 2.4 · streaming
def stream_validado(fragmentos: Iterable[str], validar: Callable[[str], bool],
                    substituto: str = " [resposta interrompida pela validação]") -> Iterator[str]:
    """Repassa o streaming frase a frase, validando cada frase antes de mostrar ao usuário."""
    buffer = ""
    for frag in fragmentos:
        buffer += frag
        while True:
            m = re.search(r"[.!?]\s", buffer)
            if not m:
                break
            frase, buffer = buffer[:m.end()], buffer[m.end():]
            if not validar(frase):
                yield substituto
                return
            yield frase
    if buffer.strip():
        if not validar(buffer):
            yield substituto
            return
        yield buffer
