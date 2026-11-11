"""Gera os vetores f de referencia em NumPy (float32, com ganho) para os 6 sinais x 2 algoritmos."""

import json
import sys
import time
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

RAIZ = Path(__file__).resolve().parents[2]
if str(RAIZ) not in sys.path:
    sys.path.insert(0, str(RAIZ))

from carga.ganho import DIMENSOES_MODELO, aplicar_ganho

DATA = RAIZ / "data"
PASTA_REF = DATA / "referencias"

SINAIS_POR_MODELO = {
    "30x30": ["g-30x30-1", "g-30x30-2", "A-30x30-1"],
    "60x60": ["G-1", "G-2", "A-60x60-1"],
}


def cgne_numpy(H: np.ndarray, g: np.ndarray, max_iter: int = 10, tol: float = 1e-4):
    f = np.zeros(H.shape[1], dtype=np.float32)
    r = g - H @ f
    p = H.T @ r
    iteracoes = 0
    erro = 0.0
    for i in range(max_iter):
        pp = float(p @ p)
        if pp == 0.0:
            break
        rr = float(r @ r)
        alpha = np.float32(rr / pp)
        f = f + alpha * p
        r_novo = r - alpha * (H @ p)
        beta = np.float32(float(r_novo @ r_novo) / rr)
        p = H.T @ r_novo + beta * p
        erro = float(abs(np.linalg.norm(r_novo) - np.linalg.norm(r)))
        r = r_novo
        iteracoes = i + 1
        if erro < tol:
            break
    return f.astype(np.float32), iteracoes, erro


def cgnr_numpy(H: np.ndarray, g: np.ndarray, max_iter: int = 10, tol: float = 1e-4):
    f = np.zeros(H.shape[1], dtype=np.float32)
    r = g - H @ f
    z = H.T @ r
    p = z.copy()
    iteracoes = 0
    erro = 0.0
    for i in range(max_iter):
        w = H @ p
        ww = float(w @ w)
        if ww == 0.0:
            break
        zz = float(z @ z)
        alpha = np.float32(zz / ww)
        f = f + alpha * p
        r_novo = r - alpha * w
        z_novo = H.T @ r_novo
        beta = np.float32(float(z_novo @ z_novo) / zz)
        p = z_novo + beta * p
        erro = float(abs(np.linalg.norm(r_novo) - np.linalg.norm(r)))
        r, z = r_novo, z_novo
        iteracoes = i + 1
        if erro < tol:
            break
    return f.astype(np.float32), iteracoes, erro


def main() -> None:
    PASTA_REF.mkdir(parents=True, exist_ok=True)
    metadados = {}

    for modelo, sinais in SINAIS_POR_MODELO.items():
        S, N, _, nome_h = DIMENSOES_MODELO[modelo]
        t_h = time.perf_counter()
        H = np.load(DATA / f"{nome_h}.npy")
        print(f"Carregado {nome_h}.npy ({H.shape}, {H.dtype}) em {time.perf_counter() - t_h:.3f} s")

        for sinal in sinais:
            g_bruto = np.load(DATA / f"{sinal}.npy").ravel().astype(np.float32)
            g = aplicar_ganho(g_bruto, S, N)

            if sinal == "g-30x30-1":
                fig, ax = plt.subplots(figsize=(6, 4))
                ax.imshow(g.reshape(S, N, order="F"), aspect="auto", cmap="viridis")
                ax.set_title("Sinograma g-30x30-1 com ganho (S=436 x N=64, order='F')")
                ax.set_xlabel("Sensor c (1..64)")
                ax.set_ylabel("Amostra l (1..436)")
                fig.tight_layout()
                fig.savefig(PASTA_REF / "sinograma_g-30x30-1.png", dpi=120)
                plt.close(fig)

            for nome_alg, fn in (("CGNE", cgne_numpy), ("CGNR", cgnr_numpy)):
                t0 = time.perf_counter()
                f, iters, erro = fn(H, g)
                dur_ms = (time.perf_counter() - t0) * 1000.0

                chave = f"{sinal}_{nome_alg}"
                np.save(PASTA_REF / f"{chave}.npy", f)
                metadados[chave] = {
                    "modelo": modelo,
                    "sinal": sinal,
                    "algoritmo": nome_alg,
                    "iteracoes": iters,
                    "erro_final": erro,
                    "tempo_py_ms": round(dur_ms, 3),
                    "norma_f": float(np.linalg.norm(f)),
                }
                print(
                    f"[Ref Py] {chave:18s} | iter={iters:2d} | erro={erro:.6e} | "
                    f"tempo={dur_ms:7.2f} ms | ||f||={np.linalg.norm(f):.4e}"
                )

    with open(PASTA_REF / "metadados_referencias.json", "w", encoding="utf-8") as arq:
        json.dump(metadados, arq, indent=2, ensure_ascii=False)
    print(f"Referencias salvas em {PASTA_REF.relative_to(RAIZ)}")


if __name__ == "__main__":
    main()

