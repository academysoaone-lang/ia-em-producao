"""Utilitários de texto e um embedder local (sem download de modelo)."""
from __future__ import annotations

import hashlib
import math
import re
import unicodedata

PALAVRAS_VAZIAS = set("""a o as os um uma uns umas de do da dos das em no na nos nas por para pra com
sem e ou que se é ser são foi há ao aos à às meu minha seu sua eu você voce ele ela nós isso isto este
esta esse essa qual quais como quando onde mais menos muito pouco já não nao sim tem ter
quanto quanta quantos quantas vocês voces posso pode podem fazer faz funciona sobre""".split())


def normalizar(texto: str) -> str:
    """Minúsculas e sem acentos: 'Devolução' -> 'devolucao'."""
    t = unicodedata.normalize("NFKD", texto.lower())
    return "".join(c for c in t if not unicodedata.combining(c))


def palavras(texto: str, tirar_vazias: bool = True) -> list[str]:
    ws = re.findall(r"[a-z0-9]+", normalizar(texto))
    return [w for w in ws if not (tirar_vazias and w in PALAVRAS_VAZIAS)]


def _radical(w: str) -> str:
    # radicalização bem simples para português: devolução/devolver/devolvido -> devol
    for suf in ("coes", "cao", "mente", "idade", "ados", "idas", "idos", "ando", "endo", "ado", "ido",
                "ada", "ida", "ar", "er", "ir", "es", "s"):
        if len(w) > len(suf) + 3 and w.endswith(suf):
            return w[: -len(suf)]
    return w


def radicais(texto: str) -> list[str]:
    """Palavras significativas reduzidas ao radical: 'reembolsos devolvidos' -> ['reembol', 'devolv']."""
    return [_radical(w) for w in palavras(texto)]


class HashEmbedder:
    """Embedding por 'feature hashing' de radicais e bigramas.

    Não entende sinônimos como um modelo neural, mas é determinístico, roda
    offline e mostra todo o pipeline (vetor, normalização, similaridade de
    cosseno). Para embeddings de verdade, troque por um modelo do provedor ou
    por sentence-transformers: a interface `embed(texto) -> list[float]` é a mesma.
    """

    def __init__(self, dimensoes: int = 512):
        self.dimensoes = dimensoes

    def embed(self, texto: str) -> list[float]:
        v = [0.0] * self.dimensoes
        rs = radicais(texto)
        termos = rs + [f"{a}_{b}" for a, b in zip(rs, rs[1:])]
        for t in termos:
            h = int(hashlib.md5(t.encode()).hexdigest(), 16)
            v[h % self.dimensoes] += 1.0 if (h >> 64) & 1 else -1.0
        n = math.sqrt(sum(x * x for x in v)) or 1.0
        return [x / n for x in v]


def cosseno(a: list[float], b: list[float]) -> float:
    return sum(x * y for x, y in zip(a, b))
