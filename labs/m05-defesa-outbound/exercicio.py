"""Módulo 5 · Defesa outbound · Exercício

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
    # TODO 1a: encontre valores no formato brasileiro depois de "R$" (com ou sem espaço),
    #   com milhar opcional em ponto e centavos opcionais em vírgula, e converta para float.
    raise NotImplementedError("TODO 1a")


def validar_valores(resposta: str, catalogo: dict[str, float], desconto_maximo: int = 10) -> list[str]:
    """Confere preços e descontos citados na resposta. Devolve a lista de problemas (vazia = ok)."""
    # TODO 1b: analise frase a frase (use frases()).
    #   - Produtos citados: nomes do catálogo que aparecem na frase (compare com normalizar()).
    #   Se a frase cita produto(s) e algum valor em R$ não é o preço de nenhum deles,
    #   registre f"preço errado: R$ {valor:.2f} para {produto}" (use o primeiro produto citado).
    #   - Descontos: "N%" numa frase que fala de desconto (normalizada contém "desconto") e
    #   N > desconto_maximo -> f"desconto acima do permitido: {N}%".
    raise NotImplementedError("TODO 1b")


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
    # TODO 2: normalize o texto e procure cada termo como palavra/expressão inteira
    #   (\b no começo e no fim), também normalizado. "burro" não pode casar com "burrocracia".
    #   Em produção, isto é um modelo de moderação; a interface é a mesma.
    raise NotImplementedError("TODO 2")


# ---------------------------------------------------------------- Aula 5.3 · grounding
def checar_grounding(resposta: str, trechos: list[str], minimo: float = 0.5) -> list[str]:
    """Devolve as frases SEM apoio nos trechos recuperados (lista vazia = tudo fundamentado)."""
    # TODO 3: para cada frase da resposta:
    #   - ignore frases com menos de 3 radicais (cortesia: "Posso ajudar em algo mais?");
    #   - a frase precisa citar ao menos um trecho no formato [n], com 1 <= n <= len(trechos);
    #   - tire as citações da frase e calcule a fração dos radicais dela que aparecem nos
    #   radicais dos trechos citados. Abaixo de `minimo`, a frase não tem apoio.
    #   Este verificador lexical é o "primeiro filtro"; em produção, um segundo modelo
    #   classifica as frases que sobrarem (apoiada / contradita / sem apoio).
    raise NotImplementedError("TODO 3")


# ---------------------------------------------------------------- Aula 5.4 · sanitização
def dominio_permitido(url: str, permitidos: list[str]) -> bool:
    # TODO 4a: use urlparse. Só http/https. O host precisa ser IGUAL a um domínio permitido
    #   ou terminar em "." + domínio (subdomínio). Cuidado com:
    #   https://soaone.com.br.golpe.com, https://golpe.com/soaone.com.br e https://soaone.com.br@golpe.com
    raise NotImplementedError("TODO 4a")


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
