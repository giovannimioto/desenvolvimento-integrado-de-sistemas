"""Funções de tempo usadas nos metadados e métricas do servidor."""

from datetime import datetime


def agora_iso() -> str:
    return datetime.now().astimezone().isoformat(timespec="milliseconds")


def timestamp_arquivo() -> str:
    return datetime.now().astimezone().strftime("%Y%m%d-%H%M%S")


def diferenca_ms(inicio: float, fim: float) -> float:
    return (fim - inicio) * 1000.0
