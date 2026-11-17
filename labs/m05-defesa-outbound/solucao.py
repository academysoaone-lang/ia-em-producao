"""Módulo 5 · Defesa outbound · Solução de referência

A saída do modelo é input não confiável. Antes de chegar ao usuário ela passa por:
  1. validação de valores contra a fonte da verdade (aula 5.1);
  2. moderação de conteúdo, nos dois sentidos (aula 5.2);
  3. checagem de grounding: cada afirmação aponta para o trecho que a sustenta (aula 5.3);
  4. sanitização: HTML escapado e links só de domínios aprovados (aula 5.4).

Teste com: pytest labs/m05-defesa-outbound
"""
from __future__ import annotations

import html
import re
from urllib.parse import urlparse

from soaone_lab import normalizar, radicais


class SaidaBloqueada(Exception):
    def __init__(self, problemas: list[str]):
        super().__init__("; ".join(problemas))
        self.problemas = problemas


def frases(texto: str) -> list[str]:
    """Divide em frases, sem quebrar em 'R$ 1.299,90' nem em 'www.site.com'."""
    return [f.strip() for f in re.split(r"(?<=[.!?])\s+(?=[A-ZÁÉÍÓÚÂÊÔÃÕÇ0-9\[])", texto.strip()) if f.strip()]


# ---------------------------------------------------------------- Aula 5.1 · validação de saída
def ler_reais(texto: str) -> list[float]:
    """'R$ 1.299,90 ou R$49' -> [1299.9, 49.0]"""
    return [float(v.replace(".", "").replace(",", "."))
            for v in re.findall(r"R\$\s?(\d{1,3}(?:\.\d{3})*(?:,\d{2})?|\d+(?:,\d{2})?)", texto)]


def validar_valores(resposta: str, catalogo: dict[str, float], desconto_maximo: int = 10) -> list[str]:
    """Confere preços e descontos citados na resposta. Devolve a lista de problemas (vazia = ok)."""
    problemas = []
    for f in frases(resposta):
        nf = normalizar(f)
        citados = [p for p in catalogo if normalizar(p) in nf]
        if citados:
            validos = {round(catalogo[p], 2) for p in citados}
            for v in ler_reais(f):
                if round(v, 2) not in validos:
                    problemas.append(f"preço errado: R$ {v:.2f} para {citados[0]}")
        if "desconto" in nf:
            for n in re.findall(r"(\d{1,3})\s?%", f):
                if int(n) > desconto_maximo:
                    problemas.append(f"desconto acima do permitido: {n}%")
    return problemas


def garantir_valores(resposta: str, catalogo: dict[str, float], desconto_maximo: int = 10) -> str:
    problemas = validar_valores(resposta, catalogo, desconto_maximo)
    if problemas:
        raise SaidaBloqueada(problemas)
    return resposta


# ---------------------------------------------------------------- Aula 5.2 · moderação
LISTAS_MODERACAO = {
    "ofensa": ["idiota", "burro", "imbecil", "otario", "incompetente"],
    "promessa_indevida": ["garantimos que", "100% garantido", "sem nenhum risco", "nunca vai quebrar",
                          "com certeza absoluta"],
    "assunto_proibido": ["politica partidaria", "em quem votar", "aposta esportiva"],
}


def moderar(texto: str, listas: dict[str, list[str]] = LISTAS_MODERACAO) -> list[str]:
    """Devolve as categorias violadas, em ordem alfabética, sem repetição."""
    t = normalizar(texto)
    return sorted({cat for cat, termos in listas.items()
                   for termo in termos if re.search(rf"\b{re.escape(normalizar(termo))}\b", t)})


# ---------------------------------------------------------------- Aula 5.3 · grounding
def checar_grounding(resposta: str, trechos: list[str], minimo: float = 0.5) -> list[str]:
    """Devolve as frases SEM apoio nos trechos recuperados (lista vazia = tudo fundamentado)."""
    sem_apoio = []
    for f in frases(resposta):
        limpa = re.sub(r"\[\d+\]", "", f)
        rs = set(radicais(limpa))
        if len(rs) < 3:
            continue
        citados = [int(n) for n in re.findall(r"\[(\d+)\]", f) if 1 <= int(n) <= len(trechos)]
        if not citados:
            sem_apoio.append(f)
            continue
        base = set().union(*(radicais(trechos[n - 1]) for n in citados))
        if len(rs & base) / len(rs) < minimo:
            sem_apoio.append(f)
    return sem_apoio


# ---------------------------------------------------------------- Aula 5.4 · sanitização
def dominio_permitido(url: str, permitidos: list[str]) -> bool:
    try:
        u = urlparse(url)
    except ValueError:
        return False
    host = (u.hostname or "").lower()
    return u.scheme in ("http", "https") and any(host == d or host.endswith("." + d) for d in permitidos)


LINK_REMOVIDO = "[link removido]"


def sanitizar_saida(texto: str, permitidos: list[str]) -> str:
    # >>> TODO 4b:
    #     1. Escape o HTML (html.escape com quote=False): o navegador nunca deve executar a saída do modelo.
    #     2. Links markdown [texto](url): mantenha se o domínio for permitido; senão troque por
    #        "texto [link removido]".
    #     3. URLs soltas (http:// ou https:// ou javascript:): mantenha se permitida, senão LINK_REMOVIDO.
    #        Não processe de novo as URLs que já estavam dentro de links markdown.
    t = html.escape(texto, quote=False)

    def md(m: re.Match) -> str:
        rotulo, url = m.group(1), m.group(2)
        return m.group(0) if dominio_permitido(url, permitidos) else f"{rotulo} {LINK_REMOVIDO}"

    t = re.sub(r"\[([^\]]+)\]\(([^)\s]+)\)", md, t)

    def solta(m: re.Match) -> str:
        url = m.group(0).rstrip(".,;:!?")
        resto = m.group(0)[len(url):]
        return (url if dominio_permitido(url, permitidos) else LINK_REMOVIDO) + resto

    return re.sub(r"(?<!\]\()(?:https?://|javascript:)[^\s)]+", solta, t)
    # <<<
