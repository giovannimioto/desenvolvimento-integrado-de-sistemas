"""Validação das requisições e serialização das respostas HTTP."""

from __future__ import annotations

import json
import math
import time
from typing import Any

import numpy as np

from servers.python.fila import Pedido, Resposta
from servers.python.modelos import Modelo
from utilitarios import agora_iso


def _ler_json(corpo: bytes) -> dict[str, Any]:
    try:
        dados = json.loads(corpo.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise ValueError("JSON invalido") from exc
    if not isinstance(dados, dict):
        raise ValueError("JSON invalido")
    return dados


def _validar_identificacao(dados: dict[str, Any]) -> None:
    for campo in ("client_id", "signal_id", "model", "algorithm"):
        if not isinstance(dados.get(campo), str):
            raise ValueError(f"campo obrigatorio ausente ou invalido: {campo}")
    if not dados["client_id"] or not dados["signal_id"]:
        raise ValueError("client_id e signal_id nao podem ser vazios")


def _ler_vetor(dados: dict[str, Any], tamanho_esperado: int) -> np.ndarray:
    valores = dados.get("g")
    if not isinstance(valores, list):
        raise ValueError("campo 'g' deve ser um array numerico")
    if len(valores) != tamanho_esperado:
        raise ValueError(
            f"tamanho de g ({len(valores)}) diferente do esperado ({tamanho_esperado})"
        )
    if any(
        isinstance(valor, bool)
        or not isinstance(valor, (int, float))
        or not math.isfinite(float(valor))
        for valor in valores
    ):
        raise ValueError("elemento nao numerico em g")
    vetor = np.asarray(valores, dtype=np.float32)
    if not np.isfinite(vetor).all():
        raise ValueError("elemento fora do intervalo float32 em g")
    return vetor


def interpretar_pedido(corpo: bytes, modelos: dict[str, Modelo]) -> Pedido:
    dados = _ler_json(corpo)
    _validar_identificacao(dados)

    modelo = modelos.get(dados["model"])
    if modelo is None:
        raise ValueError(f"modelo desconhecido: {dados['model']}")
    if dados["algorithm"] not in ("CGNE", "CGNR"):
        raise ValueError(f"algoritmo desconhecido: {dados['algorithm']}")

    vetor = _ler_vetor(dados, modelo.matriz.shape[0])
    return Pedido(
        client_id=dados["client_id"],
        signal_id=dados["signal_id"],
        model=dados["model"],
        algorithm=dados["algorithm"],
        g=vetor,
        recebido_em=time.perf_counter(),
        recebido_at=agora_iso(),
    )


def para_json(resposta: Resposta) -> dict[str, Any]:
    return {
        "client_id": resposta.client_id, "signal_id": resposta.signal_id,
        "algorithm": resposta.algorithm, "model": resposta.model,
        "started_at": resposta.started_at, "finished_at": resposta.finished_at,
        "received_at": resposta.received_at,
        "iterations": resposta.iterations, "f": resposta.f.tolist(),
        "server": "python", "duration_ms": resposta.duration_ms,
        "wait_ms": resposta.wait_ms, "error": resposta.error,
    }
