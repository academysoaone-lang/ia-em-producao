"""Carrega o código dos labs para o projeto final.

    componentes("exercicio")  -> o SEU código de cada lab (padrão do projeto)
    componentes("solucao")    -> as soluções de referência

O projeto final não reescreve nada: ele junta as caixas que você construiu nos módulos 1 a 7.
"""
from __future__ import annotations

import importlib.util
import sys
from pathlib import Path
from types import SimpleNamespace

LABS = Path(__file__).resolve().parents[1] / "labs"
PASTAS = {
    "rag": "m01-contexto-e-rag",
    "agente": "m02-do-chatbot-ao-agente",
    "producao": "m03-production-readiness",
    "entrada": "m04-defesa-inbound",
    "saida": "m05-defesa-outbound",
    "sistemico": "m06-protecao-sistemica",
    "travas": "m07-regra-vs-trava",
}


def _carregar(pasta: str, fonte: str):
    chave = f"pf_{pasta.replace('-', '_')}_{fonte}"
    if chave in sys.modules:
        return sys.modules[chave]
    spec = importlib.util.spec_from_file_location(chave, LABS / pasta / f"{fonte}.py")
    mod = importlib.util.module_from_spec(spec)
    sys.modules[chave] = mod
    spec.loader.exec_module(mod)
    return mod


def componentes(fonte: str = "exercicio") -> SimpleNamespace:
    return SimpleNamespace(**{nome: _carregar(pasta, fonte) for nome, pasta in PASTAS.items()},
                           docs=LABS / "m01-contexto-e-rag" / "docs")
