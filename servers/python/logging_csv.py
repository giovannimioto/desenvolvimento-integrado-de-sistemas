"""Registro CSV das reconstruções concluídas."""

from __future__ import annotations

import csv
import threading
from pathlib import Path

from servers.python.fila import Resposta
from servers.python.tempo import timestamp_arquivo


class LogCsv:
    def __init__(self, pasta: Path) -> None:
        pasta.mkdir(parents=True, exist_ok=True)
        self.caminho = pasta / f"reconstrucoes_{timestamp_arquivo()}.csv"
        self._arquivo = self.caminho.open("w", newline="", encoding="utf-8")
        self._writer = csv.writer(self._arquivo)
        self._writer.writerow(("client_id", "signal_id", "algorithm", "model",
                               "started_at", "finished_at", "iterations",
                               "received_at", "wait_ms", "duration_ms", "error"))
        self._arquivo.flush()
        self._lock = threading.Lock()

    def registrar(self, resposta: Resposta) -> None:
        with self._lock:
            self._writer.writerow((resposta.client_id, resposta.signal_id,
                                   resposta.algorithm, resposta.model,
                                   resposta.started_at, resposta.finished_at,
                                   resposta.iterations, resposta.received_at,
                                   f"{resposta.wait_ms:.3f}", f"{resposta.duration_ms:.3f}",
                                   f"{resposta.error:.6e}"))
            self._arquivo.flush()

    def fechar(self) -> None:
        with self._lock:
            self._arquivo.close()
