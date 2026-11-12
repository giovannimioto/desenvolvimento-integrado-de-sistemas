"""Fase 2: operações básicas MN = M·N, aM = a·M e Ma = M·aᵀ (dados do Dados.zip)."""

import sys
import time
from pathlib import Path

import numpy as np

RAIZ = Path(__file__).resolve().parents[2]
PASTA = Path(sys.argv[1]) if len(sys.argv) > 1 else RAIZ / "data" / "fase2"


def ler(nome: str) -> np.ndarray:
    return np.loadtxt(PASTA / f"{nome}.csv", delimiter=";", dtype=np.float32, ndmin=2)


def cronometrar(operacao):
    inicio = time.perf_counter()
    resultado = operacao()
    return resultado, (time.perf_counter() - inicio) * 1e6


def main() -> None:
    M, N, a = ler("M"), ler("N"), ler("a")  # a é vetor-linha (1x10)
    MN, t_mn = cronometrar(lambda: M @ N)
    aM, t_am = cronometrar(lambda: a @ M)
    Ma, t_ma = cronometrar(lambda: M @ a.T)
    print(f"=== Fase 2: Validacao com Dados.zip ({PASTA}) ===")
    print(f"MN {MN.shape}: diff_max = {np.abs(MN - ler('MN')).max():.6f} | tempo = {t_mn:.1f} us")
    print(f"aM {aM.shape}: diff_max = {np.abs(aM - ler('aM')).max():.6f} | tempo = {t_am:.1f} us")
    print(f"Ma {Ma.shape}: norma    = {np.linalg.norm(Ma):.6f} | tempo = {t_ma:.1f} us")


if __name__ == "__main__":
    main()
