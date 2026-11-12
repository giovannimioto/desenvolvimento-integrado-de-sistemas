"""Funções auxiliares reutilizadas pelos scripts do projeto."""

from __future__ import annotations

import csv
import json
import socket
import subprocess
import time
from datetime import datetime, timedelta
from pathlib import Path

import numpy as np


# Configuração dos modelos e ganho aplicado aos sinais.

DIMENSOES_MODELO = {
    "30x30": (436, 64, 30, "H-2"),
    "60x60": (794, 64, 60, "H-1"),
}


def aplicar_ganho(g: np.ndarray, amostras: int, sensores: int) -> np.ndarray:
    vetor = np.asarray(g, dtype=np.float32).ravel()
    linhas = np.arange(1, amostras + 1, dtype=np.float32)
    gamma = 100.0 + (1.0 / 20.0) * linhas * np.sqrt(linhas)
    matriz = vetor.reshape(amostras, sensores, order="F")
    return (matriz * gamma[:, None]).ravel(order="F").astype(np.float32)


def aplicar_ganho_modelo(g: np.ndarray, modelo: str) -> np.ndarray:
    amostras, sensores, _, _ = DIMENSOES_MODELO[modelo]
    return aplicar_ganho(g, amostras, sensores)


# Horários usados nos registros do servidor.

_ANCORA_DATA = datetime.now().astimezone()
_ANCORA_PERF = time.perf_counter()


def agora_iso() -> str:
    atual = _ANCORA_DATA + timedelta(seconds=time.perf_counter() - _ANCORA_PERF)
    return atual.isoformat(timespec="milliseconds")


def timestamp_arquivo() -> str:
    return datetime.now().astimezone().strftime("%Y%m%d-%H%M%S")


def diferenca_ms(inicio: float, fim: float) -> float:
    return (fim - inicio) * 1000.0


def porta_livre() -> int:
    with socket.socket() as sock:
        sock.bind(("127.0.0.1", 0))
        return int(sock.getsockname()[1])


# Arquivos, processos e gráficos usados pelas métricas.

def ler_csv(caminho: Path) -> list[dict]:
    if not caminho.exists():
        return []
    with caminho.open("r", encoding="utf-8") as arquivo:
        return list(csv.DictReader(arquivo))


def salvar_json(caminho: Path, dados: dict) -> None:
    with caminho.open("w", encoding="utf-8") as arquivo:
        json.dump(dados, arquivo, indent=2, ensure_ascii=False)


def encerrar(processo: subprocess.Popen | None, timeout: float = 5) -> None:
    if processo is None or processo.poll() is not None:
        return
    processo.terminate()
    try:
        processo.wait(timeout=timeout)
    except subprocess.TimeoutExpired:
        processo.kill()


def salvar_grafico(
    destino: Path,
    nome: str,
    series: list[tuple[list[float], list[float], str]],
    titulo: str,
    ylabel: str,
    degrau: bool = False,
) -> None:
    import matplotlib.pyplot as plt

    fig, eixo = plt.subplots(figsize=(8, 4.2))
    for tempos, valores, legenda in series:
        desenhar = eixo.step if degrau else eixo.plot
        opcoes = {"where": "post"} if degrau else {}
        desenhar(tempos, valores, linewidth=1.8, label=legenda, **opcoes)
    eixo.set(title=titulo, xlabel="Tempo (s)", ylabel=ylabel)
    eixo.grid(True, alpha=0.3)
    eixo.legend(loc="best")
    fig.tight_layout()
    fig.savefig(destino / nome, dpi=120)
    plt.close(fig)


# Algoritmos e arquivos usados na comparação entre Python e C++.

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
        beta_numerador = (
            float(novo_z @ novo_z)
            if normal_residual
            else float(novo_r @ novo_r)
        )
        beta = np.float32(beta_numerador / numerador)
        p = novo_z + beta * p
        r, z = novo_r, novo_z
        iteracoes = iteracao + 1
        if erro < tol:
            break
    return f, iteracoes, erro


def cgne_numpy(
    H: np.ndarray,
    g: np.ndarray,
    max_iter: int = 10,
    tol: float = 1e-4,
) -> tuple[np.ndarray, int, float]:
    return _cg(H, g, False, max_iter, tol)


def cgnr_numpy(
    H: np.ndarray,
    g: np.ndarray,
    max_iter: int = 10,
    tol: float = 1e-4,
) -> tuple[np.ndarray, int, float]:
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
        str(executavel),
        "--modelo", modelo,
        "--algoritmo", algoritmo,
        "--sinal", str(sinal),
        "--pasta-dados", str(pasta_dados),
        "--ganho",
        "--saida", str(saida),
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
    sinal: str,
    algoritmo: str,
    lado: int,
    f_py: np.ndarray,
    f_cpp: np.ndarray,
    iter_py: int,
    iter_cpp: int,
    erro_rel: float,
    destino: Path,
    referencia: Path | None = None,
) -> None:
    import matplotlib.image as mpimg
    import matplotlib.pyplot as plt

    imagens = [
        (
            np.abs(f_py.reshape(lado, lado, order="F")),
            f"Python NumPy ({algoritmo})\niter={iter_py}",
        ),
        (
            np.abs(f_cpp.reshape(lado, lado, order="F")),
            f"C++ Eigen ({algoritmo})\niter={iter_cpp} | rel={erro_rel:.2e}",
        ),
    ]
    if referencia and referencia.exists():
        imagens.append(
            (mpimg.imread(referencia), f"Referencia Enunciado\n({referencia.name})")
        )
    fig, eixos = plt.subplots(1, len(imagens), figsize=(4.2 * len(imagens), 4))
    for eixo, (imagem, titulo) in zip(np.atleast_1d(eixos), imagens):
        eixo.imshow(imagem, cmap="gray")
        eixo.set_title(titulo)
        eixo.axis("off")
    fig.suptitle(f"Sinal: {sinal} ({lado}x{lado}) — {algoritmo}", fontsize=11)
    fig.tight_layout()
    fig.savefig(destino, dpi=120)
    plt.close(fig)
