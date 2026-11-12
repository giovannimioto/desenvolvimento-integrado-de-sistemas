"""Registro CSV das reconstruções concluídas."""

from __future__ import annotations

import csv
import threading
from pathlib import Path
from typing import TextIO

from servers.python.fila import Resposta
from utilitarios import timestamp_arquivo


def abrir_log(pasta: Path) -> TextIO:
    pasta.mkdir(parents=True, exist_ok=True)
    caminho = pasta / f"reconstrucoes_{timestamp_arquivo()}.csv"
    arquivo = caminho.open("w", newline="", encoding="utf-8")
    csv.writer(arquivo).writerow((
        "client_id", "signal_id", "algorithm", "model",
        "started_at", "finished_at", "iterations",
        "received_at", "wait_ms", "duration_ms", "error",
    ))
    arquivo.flush()
    return arquivo


def registrar_log(arquivo: TextIO, resposta: Resposta, lock: threading.Lock) -> None:
    with lock:
        csv.writer(arquivo).writerow((
            resposta.client_id, resposta.signal_id,
            resposta.algorithm, resposta.model,
            resposta.started_at, resposta.finished_at,
            resposta.iterations, resposta.received_at,
            f"{resposta.wait_ms:.3f}", f"{resposta.duration_ms:.3f}",
            f"{resposta.error:.6e}",
        ))
        arquivo.flush()


def fechar_log(arquivo: TextIO, lock: threading.Lock) -> None:
    with lock:
        arquivo.close()
