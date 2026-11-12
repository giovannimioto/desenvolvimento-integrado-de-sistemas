"""Validação das requisições e serialização das respostas HTTP."""

from __future__ import annotations

import json
import math
import time
from typing import Any

import numpy as np

from servers.python.fila import Pedido, Resposta
from servers.python.modelos import Modelo
from servers.python.tempo import agora_iso


def interpretar_pedido(corpo: bytes, modelos: dict[str, Modelo]) -> Pedido:
    try:
        dados = json.loads(corpo.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise ValueError("JSON invalido") from exc
    if not isinstance(dados, dict):
        raise ValueError("JSON invalido")
    for campo in ("client_id", "signal_id", "model", "algorithm"):
        if not isinstance(dados.get(campo), str):
            raise ValueError(f"campo obrigatorio ausente ou invalido: {campo}")
    if not isinstance(dados.get("g"), list):
        raise ValueError("campo 'g' deve ser um array numerico")
    if not dados["client_id"] or not dados["signal_id"]:
        raise ValueError("client_id e signal_id nao podem ser vazios")
    modelo = modelos.get(dados["model"])
    if modelo is None:
        raise ValueError(f"modelo desconhecido: {dados['model']}")
    if dados["algorithm"] not in ("CGNE", "CGNR"):
        raise ValueError(f"algoritmo desconhecido: {dados['algorithm']}")
    esperado = modelo.matriz.shape[0]
    if len(dados["g"]) != esperado:
        raise ValueError(f"tamanho de g ({len(dados['g'])}) diferente do esperado ({esperado})")
    if any(isinstance(valor, bool) or not isinstance(valor, (int, float))
           or not math.isfinite(float(valor)) for valor in dados["g"]):
        raise ValueError("elemento nao numerico em g")
    vetor = np.asarray(dados["g"], dtype=np.float32)
    if not np.isfinite(vetor).all():
        raise ValueError("elemento fora do intervalo float32 em g")
    return Pedido(dados["client_id"], dados["signal_id"], dados["model"],
                  dados["algorithm"], vetor,
                  time.perf_counter(), agora_iso())


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
