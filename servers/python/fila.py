"""Tipos e fila concorrente de reconstruções."""

from __future__ import annotations

import queue
import threading
from dataclasses import dataclass

import numpy as np


@dataclass
class Pedido:
    client_id: str
    signal_id: str
    model: str
    algorithm: str
    g: np.ndarray
    recebido_em: float
    recebido_at: str


@dataclass
class Resposta:
    client_id: str
    signal_id: str
    algorithm: str
    model: str
    started_at: str
    finished_at: str
    received_at: str
    iterations: int
    duration_ms: float
    wait_ms: float
    error: float
    f: np.ndarray


@dataclass
class Estatisticas:
    processados: int = 0
    rejeitados: int = 0
    em_processamento: int = 0


@dataclass
class Job:
    pedido: Pedido
    resultado: queue.Queue[tuple[Resposta | None, Exception | None]]


class FilaJobs:
    def __init__(self, capacidade: int) -> None:
        self._fila: queue.Queue[Job] = queue.Queue(maxsize=max(0, capacidade))
        self._fechada = False
        self._lock = threading.Lock()

    def inserir(self, job: Job) -> bool:
        with self._lock:
            if self._fechada:
                return False
            try:
                self._fila.put_nowait(job)
            except queue.Full:
                return False
            return True

    def retirar(self) -> Job | None:
        while True:
            with self._lock:
                if self._fechada and self._fila.empty():
                    return None
            try:
                return self._fila.get(timeout=0.2)
            except queue.Empty:
                continue

    def fechar(self) -> None:
        with self._lock:
            self._fechada = True

    def tamanho(self) -> int:
        return self._fila.qsize()
