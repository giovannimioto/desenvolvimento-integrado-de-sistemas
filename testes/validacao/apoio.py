"""Algoritmos NumPy e utilitários da validação C++ x Python."""

import subprocess
from pathlib import Path

import matplotlib.image as mpimg
import matplotlib.pyplot as plt
import numpy as np


def _erro(novo: np.ndarray, anterior: np.ndarray) -> float:
    return float(abs(np.linalg.norm(novo) - np.linalg.norm(anterior)))


def _cg(
    H: np.ndarray,
    g: np.ndarray,
    normal_residual: bool,
    max_iter: int,
    tol: float,
) -> tuple[np.ndarray, int, float]:
    f = np.zeros(H.shape[1], dtype=np.float32)
    r = g - H @ f
    z = H.T @ r
    p = z.copy()
    erro = 0.0
    iteracoes = 0
    for iteracao in range(max_iter):
        direcao = H @ p if normal_residual else p
        denominador = float(direcao @ direcao)
        if denominador == 0.0:
            break
        numerador = float(z @ z) if normal_residual else float(r @ r)
        alpha = np.float32(numerador / denominador)
        f = f + alpha * p
        novo_r = r - alpha * (H @ p)
        novo_z = H.T @ novo_r
        erro = _erro(novo_r, r)
        beta_numerador = float(novo_z @ novo_z) if normal_residual else float(novo_r @ novo_r)
        beta = np.float32(beta_numerador / numerador)
        p = novo_z + beta * p
        r, z = novo_r, novo_z
        iteracoes = iteracao + 1
        if erro < tol:
            break
    return f, iteracoes, erro


def cgne_numpy(H: np.ndarray, g: np.ndarray, max_iter: int = 10, tol: float = 1e-4):
    return _cg(H, g, False, max_iter, tol)


def cgnr_numpy(H: np.ndarray, g: np.ndarray, max_iter: int = 10, tol: float = 1e-4):
    return _cg(H, g, True, max_iter, tol)


ALGORITMOS = {"CGNE": cgne_numpy, "CGNR": cgnr_numpy}


def executar_cpp(
    executavel: Path,
    modelo: str,
    algoritmo: str,
    sinal: Path,
    pasta_dados: Path,
    saida: Path,
) -> tuple[np.ndarray, dict[str, str]]:
    comando = [
        str(executavel), "--modelo", modelo, "--algoritmo", algoritmo,
        "--sinal", str(sinal), "--pasta-dados", str(pasta_dados),
        "--ganho", "--saida", str(saida),
    ]
    processo = subprocess.run(comando, capture_output=True, text=True, check=True)
    campos = {
        chave: valor
        for token in processo.stdout.strip().split()
        if "=" in token
        for chave, valor in [token.split("=", 1)]
    }
    return np.loadtxt(saida, dtype=np.float32).ravel(), campos


def salvar_comparacao_png(
    sinal: str, algoritmo: str, lado: int, f_py: np.ndarray, f_cpp: np.ndarray,
    iter_py: int, iter_cpp: int, erro_rel: float, destino: Path,
    referencia: Path | None = None,
) -> None:
    imagens = [
        (np.abs(f_py.reshape(lado, lado, order="F")), f"Python NumPy ({algoritmo})\niter={iter_py}"),
        (np.abs(f_cpp.reshape(lado, lado, order="F")),
         f"C++ Eigen ({algoritmo})\niter={iter_cpp} | rel={erro_rel:.2e}"),
    ]
    if referencia and referencia.exists():
        imagens.append((mpimg.imread(referencia), f"Referencia Enunciado\n({referencia.name})"))
    fig, eixos = plt.subplots(1, len(imagens), figsize=(4.2 * len(imagens), 4))
    for eixo, (imagem, titulo) in zip(np.atleast_1d(eixos), imagens):
        eixo.imshow(imagem, cmap="gray")
        eixo.set_title(titulo)
        eixo.axis("off")
    fig.suptitle(f"Sinal: {sinal} ({lado}x{lado}) — {algoritmo}", fontsize=11)
    fig.tight_layout()
    fig.savefig(destino, dpi=120)
    plt.close(fig)
