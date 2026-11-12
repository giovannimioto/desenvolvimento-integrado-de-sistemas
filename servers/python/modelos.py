"""Carregamento único das matrizes H dos modelos disponíveis."""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from servers.python.config import Config
from utilitarios import DIMENSOES_MODELO


@dataclass(frozen=True)
class Modelo:
    nome: str
    lado: int
    amostras: int
    sensores: int
    matriz: np.ndarray


def carregar_modelos(config: Config) -> dict[str, Modelo]:
    """Carrega cada matriz uma vez e deixa-a pronta para os workers."""
    modelos: dict[str, Modelo] = {}
    for nome in (item.strip() for item in config.modelos.split(",")):
        if not nome:
            continue
        try:
            amostras, sensores, lado, nome_h = DIMENSOES_MODELO[nome]
        except KeyError as exc:
            raise ValueError(f"modelo desconhecido na configuracao: {nome}") from exc
        linhas = amostras * sensores
        colunas = lado * lado
        caminho = config.pasta_dados / f"{nome_h}.bin"
        elementos = linhas * colunas
        if not caminho.exists():
            raise FileNotFoundError(f"arquivo nao encontrado: {caminho}")
        if caminho.stat().st_size != elementos * np.dtype(np.float32).itemsize:
            raise ValueError(f"tamanho inesperado em {caminho}")
        matriz = np.fromfile(caminho, dtype=np.float32, count=elementos)
        if nome in modelos:
            raise ValueError(f"modelo repetido na configuracao: {nome}")
        modelos[nome] = Modelo(
            nome=nome,
            lado=lado,
            amostras=amostras,
            sensores=sensores,
            matriz=matriz.reshape((linhas, colunas)),
        )
        print(f"[Modelos] {nome} ({linhas}x{colunas}, "
              f"{matriz.nbytes / (1024 * 1024):.2f} MB) carregado")
    if not modelos:
        raise ValueError("nenhum modelo foi carregado")
    return modelos
