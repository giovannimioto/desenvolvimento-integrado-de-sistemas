"""Orquestra experimentos de ponta a ponta (servidor + monitor psutil + carga + relatorio R1-R7)."""

import argparse
import json
import shutil
import socket
import subprocess
import sys
import time
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import requests

RAIZ = Path(__file__).resolve().parents[1]
if str(RAIZ) not in sys.path:
    sys.path.insert(0, str(RAIZ))

from carga.gerador_carga import executar_carga
from carga.sequencia import gerar_sequencia, ler_sequencia_jsonl, salvar_sequencia_jsonl
from metricas.relatorio import gerar_relatorio_comparativo, gerar_relatorio_unico

BIN_SERVIDOR_CPP = RAIZ / "servers" / "cpp" / "build" / "servidor"
SCRIPT_MONITOR = RAIZ / "metricas" / "monitor.py"
PASTA_RESULTADOS = RAIZ / "resultados"


def escolher_porta_livre() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(("127.0.0.1", 0))
        return int(s.getsockname()[1])


def aguardar_status(url_base: str, timeout_s: float = 120.0) -> None:
    fim = time.perf_counter() + timeout_s
    url = f"{url_base.rstrip('/')}/status"
    while time.perf_counter() < fim:
        try:
            r = requests.get(url, timeout=0.5)
            if r.status_code == 200:
                return
        except Exception:
            pass
        time.sleep(0.15)
    raise TimeoutError(f"Servidor nao respondeu em {url} apos {timeout_s} s")


def rodar_experimento_unico(
    nome: str,
    itens_sequencia: list[dict],
    workers: int = 4,
    max_queue: int = 0,
    modelos: str = "30x30,60x60",
    intervalo_monitor: float = 0.25,
    pasta_saida: Path | None = None,
    cmd_customizado: list[str] | None = None,
    servidor_tipo: str = "cpp",
) -> dict:
    destino = pasta_saida or (PASTA_RESULTADOS / nome)
    if destino.exists():
        shutil.rmtree(destino)
    destino.mkdir(parents=True, exist_ok=True)
    pasta_logs_srv = destino / "logs_servidor"
    pasta_logs_srv.mkdir(parents=True, exist_ok=True)

    salvar_sequencia_jsonl(itens_sequencia, destino / "sequencia.jsonl")

    porta = escolher_porta_livre()
    url = f"http://127.0.0.1:{porta}"

    if cmd_customizado is not None:
        cmd_srv = cmd_customizado
    else:
        cmd_srv = [
            str(BIN_SERVIDOR_CPP),
            "--port", str(porta),
            "--workers", str(workers),
            "--max-queue", str(max_queue),
            "--modelos", modelos,
            "--data-dir", str(RAIZ / "data"),
            "--log-dir", str(pasta_logs_srv),
        ]

    proc_srv = subprocess.Popen(
        cmd_srv,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
    )
    proc_mon = None
    try:
        aguardar_status(url, timeout_s=120.0)

        cmd_mon = [
            sys.executable,
            str(SCRIPT_MONITOR),
            "--pid", str(proc_srv.pid),
            "--url", url,
            "--intervalo", str(intervalo_monitor),
            "--saida", str(destino / "amostras.csv"),
        ]
        proc_mon = subprocess.Popen(cmd_mon)
        time.sleep(max(0.2, intervalo_monitor))

        res_carga = executar_carga(
            url_base=url,
            itens_sequencia=itens_sequencia,
            pasta_dados=RAIZ / "data",
            caminho_respostas=destino / "respostas.jsonl",
        )
        time.sleep(max(0.2, intervalo_monitor))
    finally:
        if proc_mon is not None and proc_mon.poll() is None:
            proc_mon.terminate()
            try:
                proc_mon.wait(timeout=5)
            except subprocess.TimeoutExpired:
                proc_mon.kill()

        if proc_srv.poll() is None:
            proc_srv.terminate()
            try:
                saida_srv, _ = proc_srv.communicate(timeout=10)
            except subprocess.TimeoutExpired:
                proc_srv.kill()
                saida_srv, _ = proc_srv.communicate()
        else:
            saida_srv, _ = proc_srv.communicate()

        with open(destino / "servidor_stdout.log", "w", encoding="utf-8") as arq:
            arq.write(saida_srv or "")

    csvs_gerados = sorted(pasta_logs_srv.glob("reconstrucoes_*.csv"))
    if csvs_gerados:
        shutil.copy2(csvs_gerados[-1], destino / "reconstrucoes.csv")

    meta = {
        "nome": nome,
        "servidor": servidor_tipo,
        "workers": workers,
        "max_queue": max_queue,
        "modelos": modelos,
        "intervalo_monitor_s": intervalo_monitor,
        **res_carga["resumo"],
    }
    with open(destino / "meta.json", "w", encoding="utf-8") as arq:
        json.dump(meta, arq, indent=2, ensure_ascii=False)

    resumo = gerar_relatorio_unico(destino)
    print(
        f"[{nome}] R1={resumo['r1_total_imagens']} | R2={resumo['r2_tempo_total_s']:.2f}s | "
        f"R5={resumo['r5_fila_media']:.2f} | R6={resumo['r6_fila_moda']} | "
        f"R7={resumo['r7_tempo_medio_reconstrucao_ms']:.1f}ms | "
        f"vazao={resumo['vazao_imagens_por_s']:.2f} img/s | 503={resumo['rejeicoes_503']}"
    )
    return resumo


def executar_e0_varredura() -> tuple[int, dict]:
    print("\n=== E0: Varredura de Workers (30x30 e 60x60) ===")
    pasta_e0 = PASTA_RESULTADOS / "E0_varredura_workers"
    pasta_e0.mkdir(parents=True, exist_ok=True)

    workers_lista = [1, 2, 3, 4, 6, 8, 12]
    seq_30 = gerar_sequencia(
        clientes=6, sinais_por_cliente=4, seed=100,
        intervalo_min=0.0, intervalo_max=0.05, modelos=["30x30"],
    )
    seq_60 = gerar_sequencia(
        clientes=6, sinais_por_cliente=2, seed=200,
        intervalo_min=0.0, intervalo_max=0.05, modelos=["60x60"],
    )

    resultados_30 = []
    resultados_60 = []
    for w in workers_lista:
        r30 = rodar_experimento_unico(
            nome=f"E0_30x30_W{w}",
            itens_sequencia=seq_30,
            workers=w,
            max_queue=0,
            modelos="30x30",
            intervalo_monitor=0.15,
            pasta_saida=pasta_e0 / f"30x30_W{w}",
        )
        resultados_30.append(r30)

        r60 = rodar_experimento_unico(
            nome=f"E0_60x60_W{w}",
            itens_sequencia=seq_60,
            workers=w,
            max_queue=0,
            modelos="60x60",
            intervalo_monitor=0.2,
            pasta_saida=pasta_e0 / f"60x60_W{w}",
        )
        resultados_60.append(r60)

    # Escolhe W_otimo: menor W que atinge >= 95% da vazao maxima de 60x60 (limitado por banda de memoria)
    max_vazao_60 = max(r["vazao_imagens_por_s"] for r in resultados_60)
    candidatos_otimos = [
        r["workers"]
        for r in resultados_60
        if r["vazao_imagens_por_s"] >= 0.95 * max_vazao_60
    ]
    w_otimo = int(min(candidatos_otimos)) if candidatos_otimos else 4

    fig, eixos = plt.subplots(1, 2, figsize=(10.5, 4.2))
    eixos[0].plot(workers_lista, [r["vazao_imagens_por_s"] for r in resultados_30], marker="o", linewidth=2)
    eixos[0].set_title("Modelo 30x30 (H-2: 96 MB)")
    eixos[0].set_xlabel("Numero de Workers (W)")
    eixos[0].set_ylabel("Vazao (imagens/s)")
    eixos[0].grid(True, alpha=0.3)

    eixos[1].plot(workers_lista, [r["vazao_imagens_por_s"] for r in resultados_60], marker="s", color="tab:orange", linewidth=2)
    eixos[1].axvline(w_otimo, color="tab:red", linestyle="--", label=f"W otimo = {w_otimo}")
    eixos[1].set_title("Modelo 60x60 (H-1: 732 MB, limitado por banda RAM)")
    eixos[1].set_xlabel("Numero de Workers (W)")
    eixos[1].set_ylabel("Vazao (imagens/s)")
    eixos[1].grid(True, alpha=0.3)
    eixos[1].legend(loc="best")

    fig.suptitle("E0 — Varredura de Workers (Vazao x W)", fontsize=12)
    fig.tight_layout()
    fig.savefig(pasta_e0 / "vazao_por_workers.png", dpi=120)
    plt.close(fig)

    dados_e0 = {
        "w_otimo": w_otimo,
        "workers_testados": workers_lista,
        "modelo_30x30": resultados_30,
        "modelo_60x60": resultados_60,
    }
    with open(pasta_e0 / "resumo_e0.json", "w", encoding="utf-8") as arq:
        json.dump(dados_e0, arq, indent=2, ensure_ascii=False)

    print(f"==> W_otimo escolhido pela varredura E0: W = {w_otimo}")
    return w_otimo, dados_e0


def executar_bateria_completa(w_otimo_forcado: int | None = None) -> None:
    if w_otimo_forcado is None:
        w_otimo, _ = executar_e0_varredura()
    else:
        w_otimo = w_otimo_forcado

    print(f"\n=== E1: Baseline Oficial (3 clientes x 15 sinais, W={w_otimo}) ===")
    seq_e1 = gerar_sequencia(
        clientes=3, sinais_por_cliente=15, seed=42,
        intervalo_min=0.5, intervalo_max=2.0,
        modelos=["30x30", "60x60"],
    )
    rodar_experimento_unico(
        nome="E1_baseline_cpp",
        itens_sequencia=seq_e1,
        workers=w_otimo,
        max_queue=0,
        modelos="30x30,60x60",
        intervalo_monitor=0.25,
        pasta_saida=PASTA_RESULTADOS / "E1_baseline_cpp",
    )

    print("\n=== E2: Saturacao SEM Controle (24 clientes x 2 sinais em rajada, W=12, fila ilimitada) ===")
    seq_sat = gerar_sequencia(
        clientes=24, sinais_por_cliente=2, seed=77,
        intervalo_min=0.0, intervalo_max=0.2,
        modelos=["30x30", "60x60"],
    )
    rodar_experimento_unico(
        nome="E2_saturacao_sem_controle",
        itens_sequencia=seq_sat,
        workers=12,
        max_queue=0,
        modelos="30x30,60x60",
        intervalo_monitor=0.15,
        pasta_saida=PASTA_RESULTADOS / "E2_saturacao_sem_controle",
    )

    max_fila_e3 = 2 * w_otimo
    print(
        f"\n=== E3: Saturacao COM Controle (mesma carga E2, W={w_otimo}, "
        f"--max-queue {max_fila_e3} + HTTP 503 + retry/backoff) ==="
    )
    rodar_experimento_unico(
        nome="E3_saturacao_com_controle",
        itens_sequencia=seq_sat,
        workers=w_otimo,
        max_queue=max_fila_e3,
        modelos="30x30,60x60",
        intervalo_monitor=0.15,
        pasta_saida=PASTA_RESULTADOS / "E3_saturacao_com_controle",
    )

    gerar_relatorio_comparativo(
        PASTA_RESULTADOS / "E2_saturacao_sem_controle",
        PASTA_RESULTADOS / "E3_saturacao_com_controle",
        PASTA_RESULTADOS / "comparacao_E2_vs_E3",
    )
    print("\nBateria E0-E3 concluida! Comparacao salva em resultados/comparacao_E2_vs_E3/")


def main() -> None:
    parser = argparse.ArgumentParser(description="Executa experimento ou bateria E0-E3.")
    parser.add_argument(
        "--cenario",
        choices=["custom", "E0", "E1", "E2", "E3", "todos"],
        default="custom",
    )
    parser.add_argument("--nome", type=str, default="exp_cpp")
    parser.add_argument("--servidor", type=str, default="cpp")
    parser.add_argument("--workers", type=int, default=4)
    parser.add_argument("--max-queue", type=int, default=0)
    parser.add_argument("--clientes", type=int, default=3)
    parser.add_argument("--sinais", type=int, default=5)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--intervalo", type=float, nargs=2, default=[0.2, 0.6])
    parser.add_argument("--modelos", type=str, default="30x30,60x60")
    parser.add_argument("--sequencia", type=Path, default=None)
    parser.add_argument("--saida", type=Path, default=None)
    args = parser.parse_args()

    if args.cenario == "todos":
        executar_bateria_completa()
        return
    if args.cenario == "E0":
        executar_e0_varredura()
        return
    if args.cenario == "E1":
        seq = gerar_sequencia(3, 15, 42, 0.5, 2.0, ["30x30", "60x60"])
        rodar_experimento_unico("E1_baseline_cpp", seq, workers=args.workers, max_queue=0)
        return
    if args.cenario == "E2":
        seq = gerar_sequencia(12, 4, 77, 0.0, 0.15, ["30x30", "60x60"])
        rodar_experimento_unico("E2_saturacao_sem_controle", seq, workers=16, max_queue=0)
        return
    if args.cenario == "E3":
        seq = gerar_sequencia(12, 4, 77, 0.0, 0.15, ["30x30", "60x60"])
        rodar_experimento_unico(
            "E3_saturacao_com_controle", seq, workers=args.workers, max_queue=2 * args.workers
        )
        return

    if args.sequencia is not None:
        itens = ler_sequencia_jsonl(args.sequencia)
    else:
        modelos_lista = [m.strip() for m in args.modelos.split(",") if m.strip()]
        itens = gerar_sequencia(
            clientes=args.clientes,
            sinais_por_cliente=args.sinais,
            seed=args.seed,
            intervalo_min=args.intervalo[0],
            intervalo_max=args.intervalo[1],
            modelos=modelos_lista,
        )
    rodar_experimento_unico(
        nome=args.nome,
        itens_sequencia=itens,
        workers=args.workers,
        max_queue=args.max_queue,
        modelos=args.modelos,
        pasta_saida=args.saida,
        servidor_tipo=args.servidor,
    )


if __name__ == "__main__":
    main()
