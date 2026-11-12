"""Funções pequenas compartilhadas pelos experimentos e relatórios."""

import csv
import json
import subprocess
from pathlib import Path

import matplotlib.pyplot as plt


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
