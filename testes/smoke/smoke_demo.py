"""Smoke test portavel para ensaio e apresentacao ao vivo (perfil demo / benchmark)."""

import argparse
import json
import socket
import subprocess
import sys
import time
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import psutil
import requests

RAIZ = Path(__file__).resolve().parents[2]
if str(RAIZ) not in sys.path:
    sys.path.insert(0, str(RAIZ))

from carga.ganho import DIMENSOES_MODELO, aplicar_ganho_modelo
from carga.gerador_carga import executar_carga
from carga.sequencia import gerar_sequencia

DATA = RAIZ / "data"
PASTA_REF = DATA / "referencias"
BIN_SERVIDOR = RAIZ / "servers" / "cpp" / "build" / "servidor"

TAMANHOS_BIN = {
    "H-1.bin": 50816 * 3600 * 4,
    "H-2.bin": 27904 * 900 * 4,
}


def escolher_porta_livre() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(("127.0.0.1", 0))
        return int(s.getsockname()[1])


def main() -> None:
    parser = argparse.ArgumentParser(description="Smoke test rapido do servidor C++.")
    parser.add_argument("--perfil", choices=["demo", "benchmark"], default="demo")
    parser.add_argument("--url", type=str, default=None, help="Usa servidor ja em execucao.")
    args = parser.parse_args()

    workers = 2 if args.perfil == "demo" else 4
    max_queue = 4 if args.perfil == "demo" else 8

    etapas: list[tuple[str, bool, str]] = []

    def registrar(nome: str, ok: bool, detalhe: str) -> None:
        etapas.append((nome, ok, detalhe))
        status = "PASS" if ok else "FAIL"
        print(f"[{status}] {nome:38s} | {detalhe}")

    # 1. Conferencia dos arquivos .bin e memoria RAM livre
    bins_ok = True
    detalhes_bin = []
    for nome_arq, tam_esp in TAMANHOS_BIN.items():
        p = DATA / nome_arq
        if not p.exists() or p.stat().st_size != tam_esp:
            bins_ok = False
            detalhes_bin.append(f"{nome_arq} ausente/invalido")
        else:
            detalhes_bin.append(f"{nome_arq} OK ({tam_esp // (1024*1024)} MB)")
    ram_livre_gb = psutil.virtual_memory().available / (1024.0 ** 3)
    alerta_ram = " (ALERTA: < 2 GB)" if ram_livre_gb < 2.0 else ""
    registrar(
        "1. Dados .bin e RAM disponivel",
        bins_ok,
        f"{', '.join(detalhes_bin)} | RAM livre: {ram_livre_gb:.2f} GB{alerta_ram}",
    )
    if not bins_ok:
        sys.exit(1)

    # 2. Subir o servidor C++ (ou conectar ao --url)
    proc_srv = None
    pasta_smoke = RAIZ / "resultados" / f"smoke_{args.perfil}"
    pasta_smoke.mkdir(parents=True, exist_ok=True)

    if args.url:
        url = args.url.rstrip("/")
    else:
        porta = escolher_porta_livre()
        url = f"http://127.0.0.1:{porta}"
        cmd = [
            str(BIN_SERVIDOR),
            "--port", str(porta),
            "--workers", str(workers),
            "--max-queue", str(max_queue),
            "--modelos", "30x30,60x60",
            "--data-dir", str(DATA),
            "--log-dir", str(pasta_smoke / "logs"),
        ]
        proc_srv = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)

    try:
        # 3. GET /status
        t0 = time.perf_counter()
        status_ok = False
        dados_status = {}
        while time.perf_counter() - t0 < 90.0:
            try:
                r = requests.get(f"{url}/status", timeout=0.5)
                if r.status_code == 200:
                    status_ok = True
                    dados_status = r.json()
                    break
            except Exception:
                pass
            time.sleep(0.15)
        registrar(
            "2/3. Subida do servidor e GET /status",
            status_ok,
            f"workers={dados_status.get('workers')}, max_queue={dados_status.get('max_queue')}, "
            f"tempo_boot={time.perf_counter() - t0:.2f}s",
        )
        if not status_ok:
            sys.exit(1)

        # 4. 1 reconstrucao 30x30 CGNE + 1 reconstrucao 60x60 CGNR
        tempos_modelo = {}
        for modelo, sinal, alg in (("30x30", "g-30x30-1", "CGNE"), ("60x60", "G-1", "CGNR")):
            g_arr = np.fromfile(DATA / f"{sinal}.bin", dtype=np.float32)
            g_ganho = aplicar_ganho_modelo(g_arr, modelo)
            r = requests.post(
                f"{url}/reconstruir",
                json={
                    "client_id": "smoke",
                    "signal_id": f"smoke_{sinal}",
                    "model": modelo,
                    "algorithm": alg,
                    "g": g_ganho.tolist(),
                },
                timeout=30.0,
            )
            ok_req = r.status_code == 200
            det = f"HTTP {r.status_code}"
            if ok_req:
                corpo = r.json()
                _, _, lado, _ = DIMENSOES_MODELO[modelo]
                f_srv = np.asarray(corpo["f"], dtype=np.float32)
                tempos_modelo[modelo] = float(corpo["duration_ms"])

                fig, ax = plt.subplots(figsize=(4, 4))
                ax.imshow(np.abs(f_srv.reshape(lado, lado, order="F")), cmap="gray")
                ax.set_title(f"{sinal} ({modelo}, {alg}) - {corpo['duration_ms']:.1f} ms")
                ax.axis("off")
                fig.tight_layout()
                png_out = pasta_smoke / f"smoke_{sinal}_{alg}.png"
                fig.savefig(png_out, dpi=110)
                plt.close(fig)

                arq_ref = PASTA_REF / f"{sinal}_{alg}.npy"
                if arq_ref.exists():
                    f_ref = np.load(arq_ref).ravel()
                    erro_rel = float(np.linalg.norm(f_srv - f_ref) / np.linalg.norm(f_ref))
                    ok_req = ok_req and (erro_rel < 1e-3)
                    det = f"iter={corpo['iterations']}, {corpo['duration_ms']:.1f} ms, erro_rel={erro_rel:.2e}, PNG salvo"
                else:
                    det = f"iter={corpo['iterations']}, {corpo['duration_ms']:.1f} ms, PNG salvo"
            registrar(f"4. Reconstrucao {modelo} ({alg})", ok_req, det)

        # 5. Mini carga: 3 clientes x 5 sinais mistos
        seq_mini = gerar_sequencia(
            clientes=3,
            sinais_por_cliente=5,
            seed=42,
            intervalo_min=0.1,
            intervalo_max=0.3,
            modelos=["30x30", "60x60"],
        )
        res_mini = executar_carga(url_base=url, itens_sequencia=seq_mini, pasta_dados=DATA)
        ok_mini = res_mini["resumo"]["sucesso_200"] == 15 and res_mini["resumo"]["erros_finais"] == 0
        registrar(
            "5. Mini carga (3 clientes x 5 sinais)",
            ok_mini,
            f"200_OK={res_mini['resumo']['sucesso_200']}/15, "
            f"tempo={res_mini['resumo']['tempo_parede_s']:.2f}s, "
            f"503_retries={res_mini['resumo']['rejeicoes_503']}",
        )

        # 6. Teste de controle: rajada curta -> confirma pelo menos um 503 e recuperacao via retry
        total_rajada = workers + max_queue + 6
        seq_rajada = [
            {
                "client_id": f"r{i}",
                "signal_id": f"r{i}-s01",
                "model": "60x60",
                "signal_file": "G-1",
                "algorithm": "CGNR",
                "delay_s": 0.0,
            }
            for i in range(1, total_rajada + 1)
        ]
        res_raj = executar_carga(
            url_base=url,
            itens_sequencia=seq_rajada,
            pasta_dados=DATA,
            max_tentativas=10,
            backoff_inicial=0.4,
        )
        ok_ctrl = (
            res_raj["resumo"]["rejeicoes_503"] > 0
            and res_raj["resumo"]["sucesso_200"] == total_rajada
        )
        registrar(
            "6. Controle de sobrecarga (503 + retry)",
            ok_ctrl,
            f"rejeicoes_503={res_raj['resumo']['rejeicoes_503']}, "
            f"recuperados={res_raj['resumo']['sucesso_200']}/{total_rajada}",
        )
    finally:
        if proc_srv is not None:
            proc_srv.terminate()
            try:
                proc_srv.wait(timeout=10)
            except subprocess.TimeoutExpired:
                proc_srv.kill()
            registrar(
                "7. Encerramento limpo (SIGTERM)",
                proc_srv.returncode == 0,
                f"exit_code={proc_srv.returncode}",
            )

    print("\n=== Resumo Smoke Test (" + args.perfil + ") ===")
    for modelo, t_ms in tempos_modelo.items():
        print(f" - Tempo medio {modelo}: {t_ms:.1f} ms")
    falhas = [nome for nome, ok, _ in etapas if not ok]
    if falhas:
        print("RESULTADO FINAL: FAIL ->", ", ".join(falhas))
        sys.exit(1)
    print("RESULTADO FINAL: PASS (100% das etapas aprovadas)")


if __name__ == "__main__":
    main()

