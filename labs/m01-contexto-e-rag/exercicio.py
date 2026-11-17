"""Módulo 1 · O cérebro expandido: contexto, RAG e embeddings

Você vai construir, do zero e sem bibliotecas de RAG:
  1. uma conversa com memória e janela de tokens (aula 1.1);
  2. o chunking com sobreposição (aula 1.4);
  3. a busca híbrida com filtro de permissão ANTES da busca (aulas 1.3 e 1.4);
  4. a resposta com contexto e a saída "não encontrei" (aula 1.2).

Teste com: pytest labs/m01-contexto-e-rag
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path

from soaone_lab import LLM, HashEmbedder, Mensagem, contar_tokens, cosseno, radicais

NAO_ENCONTREI = "Não encontrei essa informação na nossa documentação. Posso te passar para um atendente?"


# ---------------------------------------------------------------- Aula 1.1 · o modelo é stateless
class Conversa:
    def __init__(self, llm: LLM, sistema: str, max_tokens_historico: int = 2000):
        self.llm = llm
        self.sistema = sistema
        self.max_tokens_historico = max_tokens_historico
        self.historico: list[Mensagem] = []

    def janela(self) -> list[Mensagem]:
        """TODO 1a: devolva as mensagens MAIS RECENTES de self.historico cuja soma de tokens
        (use contar_tokens(m["content"])) não passe de self.max_tokens_historico.
        Mantenha a ordem cronológica no resultado."""
        raise NotImplementedError("TODO 1a: Conversa.janela")

    def perguntar(self, texto: str) -> str:
        """TODO 1b: o modelo não lembra de nada. A aplicação é que guarda e reenvia.
        1. Acrescente a mensagem do usuário ao histórico.
        2. Envie [mensagem de sistema] + self.janela() para self.llm.chat.
        3. Acrescente a resposta (role "assistant") ao histórico e devolva o texto."""
        raise NotImplementedError("TODO 1b: Conversa.perguntar")


# ---------------------------------------------------------------- Aula 1.4 · chunking
def fatiar(texto: str, tamanho: int = 60, sobreposicao: int = 15) -> list[str]:
    """TODO 2: corte o texto em trechos de `tamanho` palavras, cada um repetindo as
    últimas `sobreposicao` palavras do anterior. Levante ValueError se sobreposicao >= tamanho.
    Texto vazio devolve []. O último trecho pode ser menor; não gere trechos repetidos no fim."""
    raise NotImplementedError("TODO 2: fatiar")


@dataclass
class Documento:
    id: str
    texto: str
    grupos: list[str]


def carregar_documentos(pasta: str | Path) -> list[Documento]:
    docs = []
    for arq in sorted(Path(pasta).glob("*.md")):
        bruto = arq.read_text(encoding="utf-8")
        grupos = ["publico"]
        m = re.match(r"---\s*\n(.*?)\n---\s*\n", bruto, re.S)
        if m:
            g = re.search(r"grupos:\s*\[(.*?)\]", m.group(1))
            if g:
                grupos = [x.strip() for x in g.group(1).split(",") if x.strip()]
            bruto = bruto[m.end():]
        docs.append(Documento(arq.stem, bruto.strip(), grupos))
    return docs


# ---------------------------------------------------------------- Aulas 1.2 a 1.4 · índice e busca híbrida
@dataclass
class Trecho:
    doc_id: str
    texto: str
    grupos: list[str]
    vetor: list[float] = field(repr=False, default_factory=list)


class Indice:
    def __init__(self, embedder=None, alfa: float = 0.6):
        self.embedder = embedder or HashEmbedder()
        self.alfa = alfa  # peso da busca vetorial; (1 - alfa) vai para palavra-chave
        self.trechos: list[Trecho] = []

    def adicionar(self, doc: Documento, tamanho: int = 60, sobreposicao: int = 15) -> None:
        for paragrafo in re.split(r"\n\s*\n", doc.texto):
            paragrafo = paragrafo.strip().lstrip("# ").strip()
            for t in fatiar(paragrafo, tamanho, sobreposicao):
                self.trechos.append(Trecho(doc.id, t, doc.grupos, self.embedder.embed(t)))

    @staticmethod
    def _palavra_chave(pergunta: str, trecho: str) -> float:
        """TODO 3a: fração dos radicais da pergunta (use radicais()) que aparecem no trecho.
        Pergunta sem radicais vale 0.0."""
        raise NotImplementedError("TODO 3a: Indice._palavra_chave")

    def buscar(self, pergunta: str, grupos_usuario: list[str], k: int = 3) -> list[tuple[float, Trecho]]:
        """TODO 3b: busca híbrida com filtro de permissão.
        1. PRIMEIRO descarte os trechos sem nenhum grupo em comum com grupos_usuario.
           (Filtrar depois da busca vaza dados: o trecho proibido já ocupou uma vaga no top-k.)
        2. Pontue: alfa * cosseno(vetor da pergunta, t.vetor) + (1 - alfa) * _palavra_chave.
        3. Devolva os k melhores como [(pontuacao, trecho)], do maior para o menor."""
        raise NotImplementedError("TODO 3b: Indice.buscar")


# ---------------------------------------------------------------- Aula 1.2 · RAG com saída "não sei"
SISTEMA_RAG = ("Você é o atendente da Loja soaone. Responda APENAS com base nos trechos em <contexto>. "
               "Cite a fonte de cada afirmação no formato [n]. Se a resposta não estiver no contexto, "
               "diga que não encontrou a informação.")


def responder(llm: LLM, indice: Indice, pergunta: str, grupos_usuario: list[str],
              limiar: float = 0.2) -> dict:
    """TODO 4: RAG com saída "não sei".
    1. Busque os trechos e fique só com os de pontuação >= limiar.
    2. Se não sobrar nenhum, devolva {"texto": NAO_ENCONTREI, "fontes": []} SEM chamar o modelo.
    3. Monte o contexto numerado "[1] trecho...", envie SISTEMA_RAG como system e, no user,
       "<contexto>\n...\n</contexto>\n\nPergunta: ...".
    4. Devolva {"texto": resposta do modelo, "fontes": lista ordenada dos doc_id usados}."""
    raise NotImplementedError("TODO 4: responder")
