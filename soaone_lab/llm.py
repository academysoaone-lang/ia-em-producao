"""Cliente de LLM usado em todos os laboratórios.

Por padrão os labs rodam com um modelo FALSO, local e determinístico: não precisa
de chave de API, não custa nada e os testes dão sempre o mesmo resultado.

Para usar um modelo de verdade, defina no ambiente (ou no arquivo .env):

    LLM_PROVIDER=anthropic   LLM_MODEL=claude-haiku-5-5   ANTHROPIC_API_KEY=...
    LLM_PROVIDER=openai      LLM_MODEL=<modelo>           OPENAI_API_KEY=...
    LLM_PROVIDER=ollama      LLM_MODEL=llama3.2           (Ollama rodando local)

Todos os provedores devolvem o mesmo objeto `Resposta`, então o código dos labs
não muda quando você troca de modelo.
"""
from __future__ import annotations

import json
import os
import re
import urllib.request
from dataclasses import dataclass, field
from typing import Any, Callable, Iterable, Iterator, Protocol

from .tokens import contar_tokens

Mensagem = dict[str, Any]  # {"role": "system"|"user"|"assistant"|"tool", "content": str, ...}


@dataclass
class ChamadaFerramenta:
    """Pedido do modelo para executar uma ferramenta. O modelo PEDE; quem executa é o seu código."""
    nome: str
    argumentos: dict[str, Any]
    id: str = "call_1"


@dataclass
class Uso:
    entrada: int = 0
    saida: int = 0
    entrada_cache: int = 0  # tokens de entrada servidos do cache de prompt

    @property
    def total(self) -> int:
        return self.entrada + self.saida


@dataclass
class Resposta:
    texto: str = ""
    ferramentas: list[ChamadaFerramenta] = field(default_factory=list)
    uso: Uso = field(default_factory=Uso)
    modelo: str = "falso"


class LLM(Protocol):
    nome: str

    def chat(self, mensagens: list[Mensagem], ferramentas: list[dict] | None = None) -> Resposta: ...


class ErroProvedor(RuntimeError):
    """Falha do provedor (fora do ar, limite de taxa, timeout). Usado nos labs de fallback."""


# --------------------------------------------------------------------------------------
# Modelo falso
# --------------------------------------------------------------------------------------

Regra = Callable[[list[Mensagem], list[dict] | None], "Resposta | str | None"]


class FakeLLM:
    """Modelo falso e programável.

    - `respostas`: lista de respostas devolvidas em ordem (str ou Resposta).
    - `regra`: função que recebe as mensagens e devolve a resposta.
    - sem nenhum dos dois, usa `comportamento_ingenuo`, que imita os defeitos
      clássicos de um LLM sem engenharia em volta (ver módulo 0).

    Guarda todas as chamadas em `self.chamadas` para os testes inspecionarem
    exatamente o que foi enviado ao "provedor".
    """

    def __init__(self, respostas: Iterable[Resposta | str] | None = None, regra: Regra | None = None,
                 nome: str = "falso", falhas: int = 0):
        self.nome = nome
        self._fila = list(respostas or [])
        self._regra = regra
        self.falhas_restantes = falhas
        self.chamadas: list[list[Mensagem]] = []

    def chat(self, mensagens: list[Mensagem], ferramentas: list[dict] | None = None) -> Resposta:
        self.chamadas.append([dict(m) for m in mensagens])
        if self.falhas_restantes > 0:
            self.falhas_restantes -= 1
            raise ErroProvedor(f"{self.nome}: 503 Service Unavailable")
        if self._fila:
            r = self._fila.pop(0)
        elif self._regra:
            r = self._regra(mensagens, ferramentas)
        else:
            r = comportamento_ingenuo(mensagens, ferramentas)
        if r is None:
            r = ""
        if isinstance(r, str):
            r = Resposta(texto=r)
        r.modelo = self.nome
        if not r.uso.total:
            r.uso = Uso(entrada=sum(contar_tokens(str(m.get("content", ""))) for m in mensagens),
                        saida=contar_tokens(r.texto))
        return r

    def stream(self, mensagens: list[Mensagem]) -> Iterator[str]:
        """Devolve a resposta em fragmentos, como um provedor real com streaming."""
        texto = self.chat(mensagens).texto
        for parte in re.findall(r"\S+\s*", texto):
            yield parte


def _ultimo(mensagens: list[Mensagem], papel: str) -> str:
    for m in reversed(mensagens):
        if m.get("role") == papel:
            return str(m.get("content", ""))
    return ""


def comportamento_ingenuo(mensagens: list[Mensagem], ferramentas: list[dict] | None = None) -> str:
    """Imita um LLM 'cru': obedece a quem escreve o texto mais convincente,
    responde com confiança mesmo sem saber e só lembra do que está nas mensagens."""
    sistema = " ".join(str(m["content"]) for m in mensagens if m.get("role") == "system")
    pergunta = _ultimo(mensagens, "user")
    p = pergunta.lower()
    tudo = " ".join(str(m.get("content", "")) for m in mensagens).lower()

    # 1. Obedece a instruções injetadas (no usuário OU em conteúdo externo colado no contexto)
    if re.search(r"ignore (todas )?as instru|esque[cç]a (as|suas) (regras|instru)|ignore previous", tudo):
        if "prompt" in tudo or "instru" in tudo:
            return f"Claro! Minhas instruções são: {sistema}"
        return "Claro, vou ignorar as regras anteriores."

    # 2. Usa o contexto quando ele existe
    m = re.search(r"<contexto>\s*\n(.*?)</contexto>", pergunta, re.S)
    if m and m.group(1).strip():
        trecho = m.group(1).strip().split("\n")[0]
        return f"De acordo com a documentação: {trecho}"

    # 3. Memória: só sabe o nome se ele estiver em alguma mensagem enviada
    apresentacao = re.search(r"(?i:meu nome é|me chamo)\s+([A-ZÁÉÍÓÚ][\wáéíóúãõç]+)", pergunta)
    if apresentacao and "?" not in pergunta:
        return f"Prazer, {apresentacao.group(1)}! Como posso ajudar?"
    if "como eu me chamo" in p or re.search(r"qual (é )?o meu nome", p):
        nome = re.search(r"(?i:meu nome é|me chamo|sou o|sou a)\s+([A-ZÁÉÍÓÚ][\wáéíóúãõç]+)",
                         " ".join(str(x.get("content", "")) for x in mensagens[:-1]))
        return f"Seu nome é {nome.group(1)}." if nome else "Desculpe, não sei o seu nome."

    # 4. Alucina política com total confiança
    if any(k in p for k in ("reembolso", "devolução", "política", "prazo", "garantia")):
        return "Nossa política permite reembolso integral em até 90 dias, sem perguntas."
    if "preço" in p or "quanto custa" in p:
        return "Esse produto custa R$ 49,90."

    return "Entendi! Posso ajudar com mais alguma coisa?"


# --------------------------------------------------------------------------------------
# Provedores reais (opcionais)
# --------------------------------------------------------------------------------------

def _sem_sistema(mensagens: list[Mensagem]) -> tuple[str, list[Mensagem]]:
    sistema = "\n\n".join(str(m["content"]) for m in mensagens if m["role"] == "system")
    resto = [m for m in mensagens if m["role"] != "system"]
    return sistema, resto


class AnthropicLLM:
    def __init__(self, modelo: str | None = None):
        try:
            import anthropic  # type: ignore
        except ImportError as e:  # pragma: no cover
            raise RuntimeError("Instale o SDK: pip install anthropic") from e
        self.cliente = anthropic.Anthropic()
        self.nome = modelo or os.getenv("LLM_MODEL", "claude-haiku-5-5")

    def chat(self, mensagens, ferramentas=None):  # pragma: no cover - precisa de chave
        sistema, resto = _sem_sistema(mensagens)
        kw: dict[str, Any] = dict(model=self.nome, max_tokens=1024, messages=resto)
        if sistema:
            kw["system"] = sistema
        if ferramentas:
            kw["tools"] = [{"name": f["name"], "description": f.get("description", ""),
                            "input_schema": f["parameters"]} for f in ferramentas]
        try:
            r = self.cliente.messages.create(**kw)
        except Exception as e:
            raise ErroProvedor(str(e)) from e
        texto = "".join(b.text for b in r.content if b.type == "text")
        calls = [ChamadaFerramenta(b.name, dict(b.input), b.id) for b in r.content if b.type == "tool_use"]
        u = r.usage
        return Resposta(texto, calls, Uso(u.input_tokens, u.output_tokens,
                                          getattr(u, "cache_read_input_tokens", 0) or 0), self.nome)


class OpenAILLM:
    def __init__(self, modelo: str | None = None):
        try:
            import openai  # type: ignore
        except ImportError as e:  # pragma: no cover
            raise RuntimeError("Instale o SDK: pip install openai") from e
        self.cliente = openai.OpenAI()
        self.nome = modelo or os.environ["LLM_MODEL"]

    def chat(self, mensagens, ferramentas=None):  # pragma: no cover - precisa de chave
        kw: dict[str, Any] = dict(model=self.nome, messages=mensagens)
        if ferramentas:
            kw["tools"] = [{"type": "function", "function": f} for f in ferramentas]
        try:
            r = self.cliente.chat.completions.create(**kw)
        except Exception as e:
            raise ErroProvedor(str(e)) from e
        msg = r.choices[0].message
        calls = [ChamadaFerramenta(t.function.name, json.loads(t.function.arguments or "{}"), t.id)
                 for t in (msg.tool_calls or [])]
        return Resposta(msg.content or "", calls, Uso(r.usage.prompt_tokens, r.usage.completion_tokens), self.nome)


class OllamaLLM:
    """Modelo local via Ollama (https://ollama.com). Grátis e offline."""

    def __init__(self, modelo: str | None = None, url: str | None = None):
        self.nome = modelo or os.getenv("LLM_MODEL", "llama3.2")
        self.url = (url or os.getenv("OLLAMA_URL", "http://localhost:11434")).rstrip("/")

    def chat(self, mensagens, ferramentas=None):  # pragma: no cover - precisa do Ollama
        corpo: dict[str, Any] = {"model": self.nome, "messages": mensagens, "stream": False}
        if ferramentas:
            corpo["tools"] = [{"type": "function", "function": f} for f in ferramentas]
        req = urllib.request.Request(self.url + "/api/chat", json.dumps(corpo).encode(),
                                     {"Content-Type": "application/json"})
        try:
            with urllib.request.urlopen(req, timeout=120) as r:
                d = json.load(r)
        except Exception as e:
            raise ErroProvedor(str(e)) from e
        msg = d.get("message", {})
        calls = [ChamadaFerramenta(t["function"]["name"], t["function"].get("arguments") or {})
                 for t in msg.get("tool_calls") or []]
        return Resposta(msg.get("content", ""), calls,
                        Uso(d.get("prompt_eval_count", 0), d.get("eval_count", 0)), self.nome)


def criar_llm(provedor: str | None = None) -> LLM:
    """Cria o LLM configurado em LLM_PROVIDER (padrão: falso)."""
    _carregar_env()
    p = (provedor or os.getenv("LLM_PROVIDER", "falso")).lower()
    if p in ("falso", "fake", ""):
        return FakeLLM()
    if p == "anthropic":
        return AnthropicLLM()
    if p == "openai":
        return OpenAILLM()
    if p == "ollama":
        return OllamaLLM()
    raise ValueError(f"LLM_PROVIDER desconhecido: {p}")


def _carregar_env(caminho: str = ".env") -> None:
    """Lê um .env simples (CHAVE=valor) sem depender de bibliotecas."""
    if not os.path.exists(caminho):
        return
    for linha in open(caminho, encoding="utf-8"):
        linha = linha.strip()
        if linha and not linha.startswith("#") and "=" in linha:
            k, v = linha.split("=", 1)
            os.environ.setdefault(k.strip(), v.strip().strip('"').strip("'"))
