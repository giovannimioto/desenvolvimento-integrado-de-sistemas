"""Calculo do ganho de sinal (gamma_l = 100 + 0.05 * l * sqrt(l))."""

import numpy as np

# modelo -> (S amostras, N sensores, lado da imagem, prefixo da matriz H)
DIMENSOES_MODELO = {
    "30x30": (436, 64, 30, "H-2"),
    "60x60": (794, 64, 60, "H-1"),
}


def aplicar_ganho(g: np.ndarray, S: int, N: int) -> np.ndarray:
    """gamma_l = 100 + (1/20)*l*sqrt(l), l = 1..S, aplicado a cada uma das N colunas (ordem F)."""
    g_flat = np.asarray(g, dtype=np.float32).ravel()
    l = np.arange(1, S + 1, dtype=np.float32)
    gamma = (100.0 + (1.0 / 20.0) * l * np.sqrt(l)).astype(np.float32)
    return (g_flat.reshape(S, N, order="F") * gamma[:, None]).ravel(order="F").astype(np.float32)


def aplicar_ganho_modelo(g: np.ndarray, modelo: str) -> np.ndarray:
    """Aplica o ganho de sinal usando S e N tabelados para '30x30' ou '60x60'."""
    S, N, _, _ = DIMENSOES_MODELO[modelo]
    return aplicar_ganho(g, S, N)

