"""Algoritmos CGNE/CGNR e operação de ganho do sinal."""

from __future__ import annotations

import math

import numpy as np


MAX_ITERACOES = 10
TOLERANCIA = 1e-4


def cgne(h: np.ndarray, g: np.ndarray,
         max_iter: int = MAX_ITERACOES,
         tolerancia: float = TOLERANCIA) -> tuple[np.ndarray, int, float]:
    f = np.zeros(h.shape[1], dtype=np.float32)
    r = np.asarray(g, dtype=np.float32).copy()
    p = h.T @ r
    rr = float(r @ r)
    erro = 0.0
    if rr == 0.0:
        return f, 0, erro
    for iteracao in range(1, max_iter + 1):
        pp = float(p @ p)
        if pp == 0.0:
            break
        alpha = np.float32(rr / pp)
        f = f + alpha * p
        r_novo = r - alpha * (h @ p)
        rr_novo = float(r_novo @ r_novo)
        erro = abs(math.sqrt(rr_novo) - math.sqrt(rr))
        beta = np.float32(rr_novo / rr)
        p = h.T @ r_novo + beta * p
        r, rr = r_novo, rr_novo
        if erro < tolerancia:
            return f, iteracao, erro
    return f, min(max_iter, iteracao if "iteracao" in locals() else 0), erro


def cgnr(h: np.ndarray, g: np.ndarray,
         max_iter: int = MAX_ITERACOES,
         tolerancia: float = TOLERANCIA) -> tuple[np.ndarray, int, float]:
    f = np.zeros(h.shape[1], dtype=np.float32)
    r = np.asarray(g, dtype=np.float32).copy()
    z = h.T @ r
    p = z.copy()
    zz = float(z @ z)
    norma_r = float(np.linalg.norm(r))
    erro = 0.0
    if norma_r == 0.0 or zz == 0.0:
        return f, 0, erro
    for iteracao in range(1, max_iter + 1):
        w = h @ p
        ww = float(w @ w)
        if ww == 0.0:
            break
        alpha = np.float32(zz / ww)
        f = f + alpha * p
        r_novo = r - alpha * w
        z_novo = h.T @ r_novo
        zz_novo = float(z_novo @ z_novo)
        erro = abs(float(np.linalg.norm(r_novo)) - norma_r)
        beta = np.float32(zz_novo / zz)
        p = z_novo + beta * p
        r, z, zz, norma_r = r_novo, z_novo, zz_novo, float(np.linalg.norm(r_novo))
        if erro < tolerancia:
            return f, iteracao, erro
    return f, min(max_iter, iteracao if "iteracao" in locals() else 0), erro
