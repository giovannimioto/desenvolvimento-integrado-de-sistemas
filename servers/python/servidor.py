"""Ponto de entrada do servidor Python de reconstrução."""

from __future__ import annotations

import os
import sys
from pathlib import Path

# 1 thread de BLAS por worker: o paralelismo vem dos workers (evita oversubscription).
for variavel in ("OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS", "OMP_NUM_THREADS"):
    os.environ.setdefault(variavel, "1")

RAIZ = Path(__file__).resolve().parents[2]
if str(RAIZ) not in sys.path:
    sys.path.insert(0, str(RAIZ))

from servers.python.config import ler_config
from servers.python.modelos import carregar_modelos
from servers.python.servidor_http import iniciar_servidor


def main(argv: list[str] | None = None) -> None:
    config = ler_config(argv)
    modelos = carregar_modelos(config)
    iniciar_servidor(config, modelos)


if __name__ == "__main__":
    main()
