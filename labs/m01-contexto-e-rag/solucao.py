"""Módulo 1 · Solução de referência."""
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
        """As mensagens mais recentes que cabem no orçamento de tokens."""
        escolhidas, total = [], 0
        for m in reversed(self.historico):
            t = contar_tokens(m["content"])
            if total + t > self.max_tokens_historico:
                break
            escolhidas.append(m)
            total += t
        return list(reversed(escolhidas))

    def perguntar(self, texto: str) -> str:
        self.historico.append({"role": "user", "content": texto})
        mensagens = [{"role": "system", "content": self.sistema}] + self.janela()
        resposta = self.llm.chat(mensagens).texto
        self.historico.append({"role": "assistant", "content": resposta})
        return resposta


# ---------------------------------------------------------------- Aula 1.4 · chunking
def fatiar(texto: str, tamanho: int = 60, sobreposicao: int = 15) -> list[str]:
    if sobreposicao >= tamanho:
        raise ValueError("a sobreposição precisa ser menor que o tamanho do trecho")
    ws = texto.split()
    if not ws:
        return []
    passo = tamanho - sobreposicao
    trechos = []
    for i in range(0, len(ws), passo):
        trechos.append(" ".join(ws[i:i + tamanho]))
        if i + tamanho >= len(ws):
            break
    return trechos


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
        q = set(radicais(pergunta))
        if not q:
            return 0.0
        return len(q & set(radicais(trecho))) / len(q)

    def buscar(self, pergunta: str, grupos_usuario: list[str], k: int = 3) -> list[tuple[float, Trecho]]:
        permitidos = [t for t in self.trechos if set(t.grupos) & set(grupos_usuario)]  # filtro ANTES da busca
        vq = self.embedder.embed(pergunta)
        pontuados = []
        for t in permitidos:
            s = self.alfa * cosseno(vq, t.vetor) + (1 - self.alfa) * self._palavra_chave(pergunta, t.texto)
            pontuados.append((round(s, 4), t))
        pontuados.sort(key=lambda x: x[0], reverse=True)
        return pontuados[:k]


# ---------------------------------------------------------------- Aula 1.2 · RAG com saída "não sei"
SISTEMA_RAG = ("Você é o atendente da Loja soaone. Responda APENAS com base nos trechos em <contexto>. "
               "Cite a fonte de cada afirmação no formato [n]. Se a resposta não estiver no contexto, "
               "diga que não encontrou a informação.")


def responder(llm: LLM, indice: Indice, pergunta: str, grupos_usuario: list[str],
              limiar: float = 0.2) -> dict:
    achados = [(s, t) for s, t in indice.buscar(pergunta, grupos_usuario) if s >= limiar]
    if not achados:
        return {"texto": NAO_ENCONTREI, "fontes": []}
    contexto = "\n".join(f"[{i}] {t.texto}" for i, (_, t) in enumerate(achados, 1))
    mensagens = [
        {"role": "system", "content": SISTEMA_RAG},
        {"role": "user", "content": f"<contexto>\n{contexto}\n</contexto>\n\nPergunta: {pergunta}"},
    ]
    return {"texto": llm.chat(mensagens).texto, "fontes": sorted({t.doc_id for _, t in achados})}
