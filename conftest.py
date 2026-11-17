"""Escolhe se os testes de cada lab rodam contra o SEU código ou contra a solução.

    pytest labs/m04-defesa-inbound            # testa labs/m04-defesa-inbound/exercicio.py
    pytest labs/m04-defesa-inbound --solucao  # testa a solução de referência
"""
import importlib.util
import os
import sys
from pathlib import Path

import pytest

RAIZ = Path(__file__).parent
sys.path.insert(0, str(RAIZ))


def pytest_addoption(parser):
    parser.addoption("--solucao", action="store_true", help="roda os testes contra solucao.py")


def _carregar(pasta: Path, nome: str):
    arquivo = pasta / f"{nome}.py"
    chave = f"lab_{pasta.name.replace('-', '_')}_{nome}"
    spec = importlib.util.spec_from_file_location(chave, arquivo)
    mod = importlib.util.module_from_spec(spec)
    sys.modules[chave] = mod
    sys.path.insert(0, str(pasta))
    try:
        spec.loader.exec_module(mod)
    finally:
        sys.path.remove(str(pasta))
    return mod


@pytest.fixture
def lab(request):
    """O módulo que está sendo testado: exercicio.py (padrão) ou solucao.py."""
    usar_solucao = request.config.getoption("--solucao") or os.getenv("LAB") == "solucao"
    pasta = Path(request.node.fspath).parent
    return _carregar(pasta, "solucao" if usar_solucao else "exercicio")
