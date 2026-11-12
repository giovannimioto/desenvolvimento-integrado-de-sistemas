"""Executa cenários E0-E3 e registra carga, monitoramento e relatórios."""

import argparse
import json
import shutil
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
from utilitarios import encerrar, porta_livre, salvar_json
from metricas.relatorio import gerar_relatorio_comparativo, gerar_relatorio_unico

BIN_SERVIDOR = RAIZ / "servers" / "cpp" / "build" / "servidor"
SERVIDOR_PYTHON = RAIZ / "servers" / "python" / "servidor.py"
MONITOR = RAIZ / "metricas" / "monitor.py"
RESULTADOS = RAIZ / "resultados"
DATA = RAIZ / "data"
NOMES_CENARIOS = {
    "E1": "E1_baseline",
    "E2": "E2_saturacao_sem_controle",
    "E3": "E3_saturacao_com_controle",
}


def aguardar_status(url: str, limite: float = 120) -> None:
    fim = time.perf_counter() + limite
    while time.perf_counter() < fim:
        try:
            if requests.get(f"{url.rstrip('/')}/status", timeout=0.5).status_code == 200:
                return
        except requests.RequestException:
            pass
        time.sleep(0.15)
    raise TimeoutError(f"Servidor nao respondeu em {url} apos {limite} s")


def comando_servidor(tipo: str, porta: int, workers: int, fila: int,
                     modelos: str, logs: Path) -> list[str]:
    inicio = [sys.executable, str(SERVIDOR_PYTHON)] if tipo == "python" else [str(BIN_SERVIDOR)]
    return inicio + [
        "--port", str(porta), "--workers", str(workers),
        "--max-queue", str(fila), "--modelos", modelos, "--data-dir", str(DATA),
        "--log-dir", str(logs),
    ]


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
    destino = pasta_saida or RESULTADOS / nome
    if destino.exists():
        shutil.rmtree(destino)
    logs = destino / "logs_servidor"
    logs.mkdir(parents=True, exist_ok=True)
    salvar_sequencia_jsonl(itens_sequencia, destino / "sequencia.jsonl")

    porta = porta_livre()
    url = f"http://127.0.0.1:{porta}"
    comando = (
        cmd_customizado
        if cmd_customizado is not None
        else comando_servidor(servidor_tipo, porta, workers, max_queue, modelos, logs)
    )
    servidor = subprocess.Popen(comando, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
    monitor = None
    try:
        aguardar_status(url)
        monitor = subprocess.Popen([
            sys.executable, str(MONITOR), "--pid", str(servidor.pid), "--url", url,
            "--intervalo", str(intervalo_monitor), "--saida", str(destino / "amostras.csv"),
        ])
        time.sleep(max(0.2, intervalo_monitor))
        carga = executar_carga(
            url, itens_sequencia, DATA, caminho_respostas=destino / "respostas.jsonl"
        )
        time.sleep(max(0.2, intervalo_monitor))
    finally:
        encerrar(monitor)
        if servidor.poll() is None:
            servidor.terminate()
        try:
            saida, _ = servidor.communicate(timeout=10)
        except subprocess.TimeoutExpired:
            servidor.kill()
            saida, _ = servidor.communicate()
        (destino / "servidor_stdout.log").write_text(saida or "", encoding="utf-8")

    csvs = sorted(logs.glob("reconstrucoes_*.csv"))
    if csvs:
        shutil.copy2(csvs[-1], destino / "reconstrucoes.csv")
    meta = {
        "nome": nome, "servidor": servidor_tipo, "workers": workers,
        "max_queue": max_queue, "modelos": modelos,
        "intervalo_monitor_s": intervalo_monitor, **carga["resumo"],
    }
    salvar_json(destino / "meta.json", meta)
    resumo = gerar_relatorio_unico(destino)
    print(
        f"[{nome}] R1={resumo['r1_total_imagens']} | R2={resumo['r2_tempo_total_s']:.2f}s | "
        f"R5={resumo['r5_fila_media']:.2f} | R6={resumo['r6_fila_moda']} | "
        f"R7={resumo['r7_tempo_medio_reconstrucao_ms']:.1f}ms | "
        f"vazao={resumo['vazao_imagens_por_s']:.2f} img/s | 503={resumo['rejeicoes_503']}"
    )
    return resumo


def varrer_modelo(
    modelo: str, sinais: list[dict], workers: list[int], destino: Path,
    intervalo: float, servidor_tipo: str = "cpp",
):
    return [
        rodar_experimento_unico(
            f"E0_{modelo}_W{w}", sinais, workers=w, modelos=modelo,
            intervalo_monitor=intervalo, pasta_saida=destino / f"{modelo}_W{w}",
            servidor_tipo=servidor_tipo,
        )
        for w in workers
    ]


def executar_e0_varredura(servidor_tipo: str = "cpp") -> tuple[int, dict]:
    print(f"\n=== E0: Varredura de Workers ({servidor_tipo}, 30x30 e 60x60) ===")
    destino = RESULTADOS / f"E0_varredura_workers_{servidor_tipo}"
    destino.mkdir(parents=True, exist_ok=True)
    workers = [1, 2, 3, 4, 6, 8, 12]
    seq30 = gerar_sequencia(6, 4, 100, 0.0, 0.05, ["30x30"])
    seq60 = gerar_sequencia(6, 2, 200, 0.0, 0.05, ["60x60"])
    res30 = varrer_modelo("30x30", seq30, workers, destino, 0.15, servidor_tipo)
    res60 = varrer_modelo("60x60", seq60, workers, destino, 0.2, servidor_tipo)
    maior = max(r["vazao_imagens_por_s"] for r in res60)
    candidatos = [r["workers"] for r in res60 if r["vazao_imagens_por_s"] >= maior * 0.95]
    otimo = min(candidatos, default=4)

    fig, eixos = plt.subplots(1, 2, figsize=(10.5, 4.2))
    for eixo, resultados, titulo in zip(eixos, (res30, res60), ("30x30 (H-2: 96 MB)", "60x60 (H-1: 732 MB)")):
        eixo.plot(workers, [r["vazao_imagens_por_s"] for r in resultados], marker="o")
        eixo.set(title=titulo, xlabel="Numero de Workers (W)", ylabel="Vazao (imagens/s)")
        eixo.grid(True, alpha=0.3)
    eixos[1].axvline(otimo, color="tab:red", linestyle="--", label=f"W otimo = {otimo}")
    eixos[1].legend(loc="best")
    fig.tight_layout()
    fig.savefig(destino / "vazao_por_workers.png", dpi=120)
    plt.close(fig)
    dados = {"w_otimo": otimo, "workers_testados": workers, "modelo_30x30": res30, "modelo_60x60": res60}
    salvar_json(destino / "resumo_e0.json", dados)
    print(f"==> W_otimo escolhido pela varredura E0 ({servidor_tipo}): W = {otimo}")
    return otimo, dados


def executar_bateria_completa(servidor_tipo: str = "cpp", w_otimo_forcado: int | None = None) -> None:
    otimo = w_otimo_forcado if w_otimo_forcado is not None else executar_e0_varredura(servidor_tipo)[0]
    print(f"\n=== E1: Baseline Oficial ({servidor_tipo}, 3 clientes x 15 sinais, W={otimo}) ===")
    seq1 = gerar_sequencia(3, 15, 42, 0.5, 2.0, ["30x30", "60x60"])
    rodar_experimento_unico(f"E1_baseline_{servidor_tipo}", seq1, workers=otimo, servidor_tipo=servidor_tipo)

    print(f"\n=== E2: Saturacao SEM Controle ({servidor_tipo}, 24 clientes x 2 sinais) ===")
    seq2 = gerar_sequencia(24, 2, 77, 0.0, 0.2, ["30x30", "60x60"])
    rodar_experimento_unico(
        f"E2_saturacao_sem_controle_{servidor_tipo}", seq2, workers=12,
        intervalo_monitor=0.15, servidor_tipo=servidor_tipo,
    )

    fila = 2 * otimo
    print(f"\n=== E3: Saturacao COM Controle ({servidor_tipo}, W={otimo}, --max-queue {fila}) ===")
    rodar_experimento_unico(
        f"E3_saturacao_com_controle_{servidor_tipo}", seq2, workers=otimo, max_queue=fila,
        intervalo_monitor=0.15, servidor_tipo=servidor_tipo,
    )
    gerar_relatorio_comparativo(
        RESULTADOS / f"E2_saturacao_sem_controle_{servidor_tipo}",
        RESULTADOS / f"E3_saturacao_com_controle_{servidor_tipo}",
        RESULTADOS / f"comparacao_E2_vs_E3_{servidor_tipo}",
    )
    print(f"\nBateria E0-E3 concluida! Comparacao salva em resultados/comparacao_E2_vs_E3_{servidor_tipo}/")


def argumentos() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Executa experimento ou bateria E0-E3.")
    parser.add_argument("--cenario", choices=["custom", "E0", "E1", "E2", "E3", "todos"], default="custom")
    parser.add_argument("--nome", default="exp_cpp")
    parser.add_argument("--servidor", choices=["cpp", "python"], default="cpp")
    parser.add_argument("--workers", type=int, default=4)
    parser.add_argument("--max-queue", type=int, default=0)
    parser.add_argument("--clientes", type=int, default=3)
    parser.add_argument("--sinais", type=int, default=5)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--intervalo", type=float, nargs=2, default=[0.2, 0.6])
    parser.add_argument("--modelos", default="30x30,60x60")
    parser.add_argument("--sequencia", type=Path)
    parser.add_argument("--saida", type=Path)
    return parser.parse_args()


def main() -> None:
    args = argumentos()
    if args.cenario == "todos":
        executar_bateria_completa(args.servidor)
        return
    if args.cenario == "E0":
        executar_e0_varredura(args.servidor)
        return
    if args.cenario in NOMES_CENARIOS:
        if args.cenario == "E1":
            seq = gerar_sequencia(3, 15, 42, 0.5, 2.0, ["30x30", "60x60"])
        else:
            seq = gerar_sequencia(12, 4, 77, 0.0, 0.15, ["30x30", "60x60"])
        max_queue = 2 * args.workers if args.cenario == "E3" else 0
        rodar_experimento_unico(
            f"{NOMES_CENARIOS[args.cenario]}_{args.servidor}", seq,
            workers=args.workers, max_queue=max_queue, servidor_tipo=args.servidor,
        )
        return
    itens = ler_sequencia_jsonl(args.sequencia) if args.sequencia else gerar_sequencia(
        args.clientes, args.sinais, args.seed, *args.intervalo,
        [m.strip() for m in args.modelos.split(",") if m.strip()],
    )
    rodar_experimento_unico(
        args.nome, itens, args.workers, args.max_queue, args.modelos,
        pasta_saida=args.saida, servidor_tipo=args.servidor,
    )


if __name__ == "__main__":
    main()
