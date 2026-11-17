"""Mostra o seu progresso nos labs: python scripts/progresso.py"""
import re
import subprocess
import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[1]
PASTAS = sorted(p for p in (RAIZ / "labs").iterdir() if p.is_dir()) + [RAIZ / "projeto-final"]

print(f"{'Lab':34} {'Testes':>10}  Situação")
print("-" * 60)
feitos = 0
for p in PASTAS:
    r = subprocess.run([sys.executable, "-m", "pytest", str(p), "-o", "addopts=--import-mode=importlib", "-q",
                        "--no-header", "-p", "no:cacheprovider"],
                       cwd=RAIZ, capture_output=True, text=True)
    ult = (r.stdout.strip().splitlines() or [""])[-1]
    ok = int((re.search(r"(\d+) passed", ult) or [0, 0])[1])
    ruim = sum(int(x) for x in re.findall(r"(\d+) (?:failed|error)", ult))
    total = ok + ruim
    situacao = "pronto" if total and not ruim else ("em andamento" if ok else "a fazer")
    feitos += situacao == "pronto"
    barra = "#" * round(10 * ok / total) if total else ""
    print(f"{p.name:34} {ok:>4}/{total:<4}  {barra:<10} {situacao}")
print("-" * 60)
print(f"{feitos} de {len(PASTAS)} prontos")
