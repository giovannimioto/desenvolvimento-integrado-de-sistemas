"""Configuração da execução do servidor Python."""

from __future__ import annotations

import argparse
import os
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class Config:
    porta: int = 8080
    workers: int = 0
    max_fila: int = 0
    threads_http: int = 128
    pasta_dados: Path = Path("data")
    pasta_logs: Path = Path("logs/python")
    modelos: str = "30x30,60x60"


def _valor_env_int(nome: str, padrao: int) -> int:
    valor = os.environ.get(nome)
    return int(valor) if valor else padrao


def ler_config(argv: list[str] | None = None) -> Config:
    padrao_workers = max(1, (os.cpu_count() or 1) // 2)
    parser = argparse.ArgumentParser(description="Servidor Python de reconstrução de imagens.")
    parser.add_argument("--port", "--porta", type=int,
                        default=_valor_env_int("SERVIDOR_PORTA", 8080))
    parser.add_argument("--workers", type=int,
                        default=_valor_env_int("SERVIDOR_WORKERS", padrao_workers))
    parser.add_argument("--max-queue", "--max-fila", type=int,
                        default=_valor_env_int("SERVIDOR_MAX_FILA", 0))
    parser.add_argument("--http-threads", "--threads-http", type=int,
                        default=_valor_env_int("SERVIDOR_THREADS_HTTP", 128))
    parser.add_argument("--data-dir", "--pasta-dados", type=Path,
                        default=Path(os.environ.get("SERVIDOR_PASTA_DADOS", "data")))
    parser.add_argument("--log-dir", "--pasta-logs", type=Path,
                        default=Path(os.environ.get("SERVIDOR_PASTA_LOGS", "logs/python")))
    parser.add_argument("--modelos", "--models",
                        default=os.environ.get("SERVIDOR_MODELOS", "30x30,60x60"))
    args = parser.parse_args(argv)
    if args.workers <= 0:
        args.workers = padrao_workers
    if args.max_queue < 0:
        parser.error("--max-queue deve ser >= 0")
    if args.http_threads < 4:
        args.http_threads = 4
    return Config(
        porta=args.port,
        workers=args.workers,
        max_fila=args.max_queue,
        threads_http=args.http_threads,
        pasta_dados=args.data_dir,
        pasta_logs=args.log_dir,
        modelos=args.modelos,
    )
