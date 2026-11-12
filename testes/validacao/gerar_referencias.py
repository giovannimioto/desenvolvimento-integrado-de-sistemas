"""Gera referências NumPy para os sinais e algoritmos do projeto."""

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
from testes.validacao.apoio import ALGORITMOS

DATA = RAIZ / "data"
PASTA_REF = DATA / "referencias"
SINAIS = {
    "30x30": ["g-30x30-1", "g-30x30-2", "A-30x30-1"],
    "60x60": ["G-1", "G-2", "A-60x60-1"],
}


def carregar_modelo(modelo: str) -> tuple[np.ndarray, int, int]:
    amostras, sensores, _, nome_h = DIMENSOES_MODELO[modelo]
    inicio = time.perf_counter()
    H = np.load(DATA / f"{nome_h}.npy")
    print(f"Carregado {nome_h}.npy ({H.shape}, {H.dtype}) em {time.perf_counter() - inicio:.3f} s")
    return H, amostras, sensores


def salvar_sinograma(sinal: str, g: np.ndarray, amostras: int, sensores: int) -> None:
    if sinal != "g-30x30-1":
        return
    fig, ax = plt.subplots(figsize=(6, 4))
    ax.imshow(g.reshape(amostras, sensores, order="F"), aspect="auto", cmap="viridis")
    ax.set(title="Sinograma g-30x30-1 com ganho (S=436 x N=64, order='F')",
           xlabel="Sensor c (1..64)", ylabel="Amostra l (1..436)")
    fig.tight_layout()
    fig.savefig(PASTA_REF / "sinograma_g-30x30-1.png", dpi=120)
    plt.close(fig)


def gerar_caso(H: np.ndarray, g: np.ndarray, modelo: str, sinal: str, metadados: dict) -> None:
    for nome, algoritmo in ALGORITMOS.items():
        inicio = time.perf_counter()
        f, iteracoes, erro = algoritmo(H, g)
        tempo_ms = (time.perf_counter() - inicio) * 1000
        chave = f"{sinal}_{nome}"
        np.save(PASTA_REF / f"{chave}.npy", f)
        metadados[chave] = {
            "modelo": modelo, "sinal": sinal, "algoritmo": nome,
            "iteracoes": iteracoes, "erro_final": erro,
            "tempo_py_ms": round(tempo_ms, 3), "norma_f": float(np.linalg.norm(f)),
        }
        print(
            f"[Ref Py] {chave:18s} | iter={iteracoes:2d} | erro={erro:.6e} | "
            f"tempo={tempo_ms:7.2f} ms | ||f||={np.linalg.norm(f):.4e}"
        )


def main() -> None:
    PASTA_REF.mkdir(parents=True, exist_ok=True)
    metadados = {}
    for modelo, sinais in SINAIS.items():
        H, amostras, sensores = carregar_modelo(modelo)
        for sinal in sinais:
            bruto = np.load(DATA / f"{sinal}.npy").ravel().astype(np.float32)
            g = aplicar_ganho(bruto, amostras, sensores)
            salvar_sinograma(sinal, g, amostras, sensores)
            gerar_caso(H, g, modelo, sinal, metadados)
    with open(PASTA_REF / "metadados_referencias.json", "w", encoding="utf-8") as arquivo:
        json.dump(metadados, arquivo, indent=2, ensure_ascii=False)
    print(f"Referencias salvas em {PASTA_REF.relative_to(RAIZ)}")


if __name__ == "__main__":
    main()
