"""Contagem aproximada de tokens e custo.

A regra prática de ~4 caracteres por token é boa o bastante para orçamento e
limites. Para cobrança exata, use a contagem que o provedor devolve em `Resposta.uso`.
"""
from __future__ import annotations

import math

# Preço em US$ por milhão de tokens. Valores ILUSTRATIVOS para os exercícios:
# confira a tabela atual do seu provedor antes de usar em produção.
PRECOS = {
    "falso": {"entrada": 1.00, "saida": 5.00, "cache": 0.10},
    "barato": {"entrada": 0.25, "saida": 1.25, "cache": 0.03},
    "premium": {"entrada": 3.00, "saida": 15.00, "cache": 0.30},
}


def contar_tokens(texto: str) -> int:
    if not texto:
        return 0
    return max(1, math.ceil(len(texto) / 4))


def custo_usd(entrada: int, saida: int, modelo: str = "falso", entrada_cache: int = 0) -> float:
    p = PRECOS.get(modelo, PRECOS["falso"])
    normal = max(0, entrada - entrada_cache)
    return (normal * p["entrada"] + entrada_cache * p["cache"] + saida * p["saida"]) / 1_000_000
