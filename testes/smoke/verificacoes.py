"""Verificações individuais do smoke test do servidor C++."""

import time
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import psutil
import requests

from carga.ganho import DIMENSOES_MODELO, aplicar_ganho_modelo
from carga.gerador_carga import executar_carga
from carga.sequencia import gerar_sequencia

TAMANHOS_BIN = {"H-1.bin": 50816 * 3600 * 4, "H-2.bin": 27904 * 900 * 4}


def verificar_dados(data: Path) -> tuple[bool, str]:
    detalhes = []
    valido = True
    for nome, tamanho in TAMANHOS_BIN.items():
        arquivo = data / nome
        if not arquivo.exists() or arquivo.stat().st_size != tamanho:
            valido = False
            detalhes.append(f"{nome} ausente/invalido")
        else:
            detalhes.append(f"{nome} OK ({tamanho // (1024 * 1024)} MB)")
    ram_gb = psutil.virtual_memory().available / 1024**3
    alerta = " (ALERTA: < 2 GB)" if ram_gb < 2 else ""
    return valido, f"{', '.join(detalhes)} | RAM livre: {ram_gb:.2f} GB{alerta}"


def aguardar_status(url: str, limite_s: float = 90.0) -> tuple[bool, dict, float]:
    inicio = time.perf_counter()
    while time.perf_counter() - inicio < limite_s:
        try:
            resposta = requests.get(f"{url}/status", timeout=0.5)
            if resposta.status_code == 200:
                return True, resposta.json(), time.perf_counter() - inicio
        except requests.RequestException:
            pass
        time.sleep(0.15)
    return False, {}, time.perf_counter() - inicio


def testar_reconstrucoes(
    url: str, data: Path, referencias: Path, destino: Path
) -> tuple[dict[str, float], list[tuple[str, bool, str]]]:
    resultados = []
    tempos = {}
    casos = (("30x30", "g-30x30-1", "CGNE"), ("60x60", "G-1", "CGNR"))
    for modelo, sinal, algoritmo in casos:
        bruto = np.fromfile(data / f"{sinal}.bin", dtype=np.float32)
        resposta = requests.post(
            f"{url}/reconstruir",
            json={
                "client_id": "smoke", "signal_id": f"smoke_{sinal}",
                "model": modelo, "algorithm": algoritmo,
                "g": aplicar_ganho_modelo(bruto, modelo).tolist(),
            },
            timeout=30,
        )
        ok, detalhe = resposta.status_code == 200, f"HTTP {resposta.status_code}"
        if ok:
            corpo = resposta.json()
            tempos[modelo] = float(corpo["duration_ms"])
            salvar_imagem(corpo, sinal, modelo, algoritmo, destino)
            referencia = referencias / f"{sinal}_{algoritmo}.npy"
            if referencia.exists():
                f_srv = np.asarray(corpo["f"], dtype=np.float32)
                f_ref = np.load(referencia).ravel()
                erro = np.linalg.norm(f_srv - f_ref) / np.linalg.norm(f_ref)
                ok = erro < 1e-3
                detalhe = f"iter={corpo['iterations']}, {corpo['duration_ms']:.1f} ms, erro_rel={erro:.2e}, PNG salvo"
            else:
                detalhe = f"iter={corpo['iterations']}, {corpo['duration_ms']:.1f} ms, PNG salvo"
        resultados.append((f"4. Reconstrucao {modelo} ({algoritmo})", ok, detalhe))
    return tempos, resultados


def salvar_imagem(corpo: dict, sinal: str, modelo: str, algoritmo: str, destino: Path) -> None:
    _, _, lado, _ = DIMENSOES_MODELO[modelo]
    fig, eixo = plt.subplots(figsize=(4, 4))
    eixo.imshow(np.abs(np.asarray(corpo["f"]).reshape(lado, lado, order="F")), cmap="gray")
    eixo.set_title(f"{sinal} ({modelo}, {algoritmo}) - {corpo['duration_ms']:.1f} ms")
    eixo.axis("off")
    fig.tight_layout()
    fig.savefig(destino / f"smoke_{sinal}_{algoritmo}.png", dpi=110)
    plt.close(fig)


def testar_cargas(url: str, data: Path, workers: int, max_queue: int) -> list[tuple[str, bool, str]]:
    sequencia = gerar_sequencia(3, 5, seed=42, intervalo_min=0.1, intervalo_max=0.3,
                                modelos=["30x30", "60x60"])
    resultado = executar_carga(url, sequencia, data)
    resumo = resultado["resumo"]
    etapas = [("5. Mini carga (3 clientes x 5 sinais)",
               resumo["sucesso_200"] == 15 and resumo["erros_finais"] == 0,
               f"200_OK={resumo['sucesso_200']}/15, tempo={resumo['tempo_parede_s']:.2f}s, "
               f"503_retries={resumo['rejeicoes_503']}")]

    total = workers + max_queue + 6
    rajada = [{
        "client_id": f"r{i}", "signal_id": f"r{i}-s01", "model": "60x60",
        "signal_file": "G-1", "algorithm": "CGNR", "delay_s": 0.0,
    } for i in range(1, total + 1)]
    resultado = executar_carga(url, rajada, data, max_tentativas=10, backoff_inicial=0.4)
    resumo = resultado["resumo"]
    etapas.append(("6. Controle de sobrecarga (503 + retry)",
                   resumo["rejeicoes_503"] > 0 and resumo["sucesso_200"] == total,
                   f"rejeicoes_503={resumo['rejeicoes_503']}, recuperados={resumo['sucesso_200']}/{total}"))
    return etapas
