"""Calcula as metricas R1-R7, gera graficos PNG (backend Agg) e relatorios comparativos."""

import argparse
import csv
import json
from collections import Counter
from datetime import datetime
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import psutil


def ler_reconstrucoes(pasta: Path) -> list[dict]:
    candidatos = sorted(pasta.glob("reconstrucoes*.csv"))
    if not candidatos:
        return []
    linhas = []
    with open(candidatos[-1], "r", encoding="utf-8") as arq:
        leitor = csv.DictReader(arq)
        for row in leitor:
            linhas.append(row)
    return linhas


def ler_amostras(pasta: Path) -> list[dict]:
    caminho = pasta / "amostras.csv"
    if not caminho.exists():
        return []
    amostras = []
    with open(caminho, "r", encoding="utf-8") as arq:
        leitor = csv.DictReader(arq)
        for row in leitor:
            amostras.append(row)
    return amostras


def calcular_moda_inteira(valores: list[int]) -> int:
    if not valores:
        return 0
    contagem = Counter(valores)
    maior_freq = max(contagem.values())
    empatados = [val for val, freq in contagem.items() if freq == maior_freq]
    return int(min(empatados))


def gerar_graficos_experimento(pasta: Path, amostras: list[dict], resumo: dict) -> None:
    t_s = [float(a["t_s"]) for a in amostras] if amostras else [0.0, 1.0]
    cpu_proc = [float(a["cpu_proc_pct"]) for a in amostras] if amostras else [0.0, 0.0]
    cpu_sis = [float(a["cpu_sistema_pct"]) for a in amostras] if amostras else [0.0, 0.0]
    rss_mb = [float(a["rss_mb"]) for a in amostras] if amostras else [0.0, 0.0]

    n_cpus = psutil.cpu_count(logical=True) or 1
    cpu_proc_norm = [c / n_cpus for c in cpu_proc]

    # R3: Grafico de CPU
    fig, ax = plt.subplots(figsize=(7.5, 4.0))
    ax.plot(t_s, cpu_proc, label="Processo Servidor (% psutil, 100%=1 nucleo)", linewidth=1.8)
    ax.plot(t_s, cpu_proc_norm, label=f"Servidor normalizado ({n_cpus} threads)", linestyle="--")
    ax.plot(t_s, cpu_sis, label="CPU Sistema Total (%)", alpha=0.75)
    ax.set_title(f"R3 — Consumo de CPU ({pasta.name})")
    ax.set_xlabel("Tempo (s)")
    ax.set_ylabel("CPU (%)")
    ax.grid(True, alpha=0.3)
    ax.legend(loc="best", fontsize=8.5)
    fig.tight_layout()
    fig.savefig(pasta / "cpu.png", dpi=120)
    plt.close(fig)

    # R4: Grafico de Memoria
    fig, ax = plt.subplots(figsize=(7.5, 4.0))
    ax.plot(t_s, rss_mb, color="tab:green", linewidth=1.8, label="RSS Servidor (MB)")
    ax.axhline(
        resumo["rss_pico_mb"],
        color="tab:red",
        linestyle=":",
        label=f"Pico: {resumo['rss_pico_mb']:.1f} MB",
    )
    ax.set_title(f"R4 — Consumo de Memoria RSS ({pasta.name})")
    ax.set_xlabel("Tempo (s)")
    ax.set_ylabel("Memoria RSS (MB)")
    ax.grid(True, alpha=0.3)
    ax.legend(loc="best")
    fig.tight_layout()
    fig.savefig(pasta / "memoria.png", dpi=120)
    plt.close(fig)

    # Grafico da Fila (R5 / R6)
    t_fila = [float(a["t_s"]) for a in amostras if a.get("queue_size", "") != ""]
    q_vals = [int(float(a["queue_size"])) for a in amostras if a.get("queue_size", "") != ""]
    ip_vals = [
        int(float(a["in_progress"])) if a.get("in_progress", "") != "" else 0
        for a in amostras
        if a.get("queue_size", "") != ""
    ]
    if not t_fila:
        t_fila, q_vals, ip_vals = [0.0, 1.0], [0, 0], [0, 0]

    fig, ax = plt.subplots(figsize=(7.5, 4.0))
    ax.step(t_fila, q_vals, where="post", linewidth=1.8, label="Aguardando na fila (queue_size)")
    ax.step(t_fila, ip_vals, where="post", linewidth=1.4, alpha=0.8, label="Em processamento (workers)")
    ax.set_title(
        f"R5/R6 — Fila de Reconstrucao (media={resumo['r5_fila_media']:.2f}, moda={resumo['r6_fila_moda']})"
    )
    ax.set_xlabel("Tempo (s)")
    ax.set_ylabel("Numero de imagens")
    ax.grid(True, alpha=0.3)
    ax.legend(loc="best")
    fig.tight_layout()
    fig.savefig(pasta / "fila.png", dpi=120)
    plt.close(fig)


def gerar_relatorio_unico(pasta: Path) -> dict:
    reconstrucoes = ler_reconstrucoes(pasta)
    amostras = ler_amostras(pasta)

    meta = {}
    if (pasta / "meta.json").exists():
        with open(pasta / "meta.json", "r", encoding="utf-8") as arq:
            meta = json.load(arq)

    r1_total = len(reconstrucoes)

    duracoes_ms = [float(r["duration_ms"]) for r in reconstrucoes if r.get("duration_ms")]
    esperas_ms = [float(r["wait_ms"]) for r in reconstrucoes if r.get("wait_ms")]
    latencias_totais_ms = [d + w for d, w in zip(duracoes_ms, esperas_ms)]

    r2_tempo_s = 0.0
    if reconstrucoes:
        try:
            inicios = [
                datetime.fromisoformat(r.get("received_at") or r["started_at"])
                for r in reconstrucoes
            ]
            fins = [datetime.fromisoformat(r["finished_at"]) for r in reconstrucoes]
            r2_tempo_s = max(0.001, (max(fins) - min(inicios)).total_seconds())
        except Exception:
            r2_tempo_s = float(meta.get("tempo_parede_s", 0.0))
    if meta.get("tempo_parede_s") and r2_tempo_s <= 0.0:
        r2_tempo_s = float(meta["tempo_parede_s"])

    filas_validas = [
        int(float(a["queue_size"])) for a in amostras if a.get("queue_size", "") != ""
    ]
    falhas_status = sum(1 for a in amostras if a.get("queue_size", "") == "")

    cpus_proc = [float(a["cpu_proc_pct"]) for a in amostras] if amostras else [0.0]
    rss_vals = [float(a["rss_mb"]) for a in amostras] if amostras else [0.0]

    r5_media = float(np.mean(filas_validas)) if filas_validas else 0.0
    r6_moda = calcular_moda_inteira(filas_validas)
    r7_media_ms = float(np.mean(duracoes_ms)) if duracoes_ms else 0.0

    # Distribuicao por modelo (30x30 vs 60x60)
    dur_30 = [float(r["duration_ms"]) for r in reconstrucoes if r.get("model") == "30x30"]
    dur_60 = [float(r["duration_ms"]) for r in reconstrucoes if r.get("model") == "60x60"]

    resumo = {
        "experimento": pasta.name,
        "servidor": meta.get("servidor", "cpp"),
        "workers": meta.get("workers"),
        "max_queue": meta.get("max_queue"),
        "r1_total_imagens": r1_total,
        "r2_tempo_total_s": round(r2_tempo_s, 4),
        "r2_tempo_parede_s": round(float(meta.get("tempo_parede_s", r2_tempo_s)), 4),
        "r3_grafico_cpu": "cpu.png",
        "r4_grafico_memoria": "memoria.png",
        "r5_fila_media": round(r5_media, 4),
        "r6_fila_moda": r6_moda,
        "r7_tempo_medio_reconstrucao_ms": round(r7_media_ms, 3),
        "r7_tempo_medio_reconstrucao_s": round(r7_media_ms / 1000.0, 4),
        "fila_maxima": int(max(filas_validas)) if filas_validas else 0,
        "espera_media_ms": round(float(np.mean(esperas_ms)), 3) if esperas_ms else 0.0,
        "latencia_p50_ms": round(float(np.percentile(latencias_totais_ms, 50)), 3) if latencias_totais_ms else 0.0,
        "latencia_p95_ms": round(float(np.percentile(latencias_totais_ms, 95)), 3) if latencias_totais_ms else 0.0,
        "tempo_medio_30x30_ms": round(float(np.mean(dur_30)), 3) if dur_30 else 0.0,
        "tempo_medio_60x60_ms": round(float(np.mean(dur_60)), 3) if dur_60 else 0.0,
        "cpu_proc_media_pct": round(float(np.mean(cpus_proc)), 2),
        "cpu_proc_pico_pct": round(float(np.max(cpus_proc)), 2),
        "rss_media_mb": round(float(np.mean(rss_vals)), 2),
        "rss_pico_mb": round(float(np.max(rss_vals)), 2),
        "vazao_imagens_por_s": round(r1_total / r2_tempo_s, 3) if r2_tempo_s > 0 else 0.0,
        "rejeicoes_503": int(meta.get("rejeicoes_503", 0)),
        "amostras_coletadas": len(amostras),
        "falhas_status": falhas_status,
    }

    gerar_graficos_experimento(pasta, amostras, resumo)

    with open(pasta / "resumo.json", "w", encoding="utf-8") as arq:
        json.dump(resumo, arq, indent=2, ensure_ascii=False)

    md = f"""# Relatorio de Metricas R1–R7: `{pasta.name}`

| Requisito | Metrica | Valor |
|---|---|---|
| **R1** | Numero total de imagens reconstruidas | **{resumo['r1_total_imagens']}** |
| **R2** | Tempo total de execucao | **{resumo['r2_tempo_total_s']:.3f} s** (parede: {resumo['r2_tempo_parede_s']:.3f} s) |
| **R3** | Grafico de consumo de CPU | `cpu.png` (media: {resumo['cpu_proc_media_pct']:.1f}%, pico: {resumo['cpu_proc_pico_pct']:.1f}%) |
| **R4** | Grafico de consumo de memoria (RSS) | `memoria.png` (media: {resumo['rss_media_mb']:.1f} MB, pico: {resumo['rss_pico_mb']:.1f} MB) |
| **R5** | Numero medio de imagens na fila | **{resumo['r5_fila_media']:.3f}** (max: {resumo['fila_maxima']}) |
| **R6** | Numero moda de imagens na fila | **{resumo['r6_fila_moda']}** |
| **R7** | Tempo medio de reconstrucao | **{resumo['r7_tempo_medio_reconstrucao_ms']:.2f} ms** ({resumo['r7_tempo_medio_reconstrucao_s']:.4f} s) |

## Diagnostico Adicional
- **Vazao efetiva:** `{resumo['vazao_imagens_por_s']:.3f}` imagens/s
- **Tempo medio de espera na fila:** `{resumo['espera_media_ms']:.2f}` ms
- **Latencia total (fila + reconstrucao):** p50 = `{resumo['latencia_p50_ms']:.2f}` ms | p95 = `{resumo['latencia_p95_ms']:.2f}` ms
- **Tempo medio por modelo:** 30x30 = `{resumo['tempo_medio_30x30_ms']:.2f}` ms | 60x60 = `{resumo['tempo_medio_60x60_ms']:.2f}` ms
- **Rejeicoes HTTP 503 (controle de fila):** `{resumo['rejeicoes_503']}`
- **Amostras de monitoramento:** `{resumo['amostras_coletadas']}` (falhas `/status`: `{resumo['falhas_status']}`)
"""
    with open(pasta / "resumo.md", "w", encoding="utf-8") as arq:
        arq.write(md)

    return resumo


def gerar_relatorio_comparativo(pasta_a: Path, pasta_b: Path, pasta_saida: Path) -> dict:
    res_a = gerar_relatorio_unico(pasta_a)
    res_b = gerar_relatorio_unico(pasta_b)
    am_a = ler_amostras(pasta_a)
    am_b = ler_amostras(pasta_b)

    pasta_saida.mkdir(parents=True, exist_ok=True)
    rot_a = res_a["experimento"]
    rot_b = res_b["experimento"]

    # Grafico CPU sobreposto
    fig, ax = plt.subplots(figsize=(8.0, 4.2))
    ax.plot(
        [float(a["t_s"]) for a in am_a],
        [float(a["cpu_proc_pct"]) for a in am_a],
        label=f"{rot_a} (media {res_a['cpu_proc_media_pct']:.1f}%)",
        linewidth=1.8,
    )
    ax.plot(
        [float(a["t_s"]) for a in am_b],
        [float(a["cpu_proc_pct"]) for a in am_b],
        label=f"{rot_b} (media {res_b['cpu_proc_media_pct']:.1f}%)",
        linewidth=1.8,
    )
    ax.set_title("R3 — Comparacao de Consumo de CPU")
    ax.set_xlabel("Tempo (s)")
    ax.set_ylabel("CPU Processo (% psutil)")
    ax.grid(True, alpha=0.3)
    ax.legend(loc="best")
    fig.tight_layout()
    fig.savefig(pasta_saida / "cpu_comparacao.png", dpi=120)
    plt.close(fig)

    # Grafico Memoria sobreposto
    fig, ax = plt.subplots(figsize=(8.0, 4.2))
    ax.plot(
        [float(a["t_s"]) for a in am_a],
        [float(a["rss_mb"]) for a in am_a],
        label=f"{rot_a} (pico {res_a['rss_pico_mb']:.1f} MB)",
        linewidth=1.8,
    )
    ax.plot(
        [float(a["t_s"]) for a in am_b],
        [float(a["rss_mb"]) for a in am_b],
        label=f"{rot_b} (pico {res_b['rss_pico_mb']:.1f} MB)",
        linewidth=1.8,
    )
    ax.set_title("R4 — Comparacao de Consumo de Memoria (RSS)")
    ax.set_xlabel("Tempo (s)")
    ax.set_ylabel("Memoria RSS (MB)")
    ax.grid(True, alpha=0.3)
    ax.legend(loc="best")
    fig.tight_layout()
    fig.savefig(pasta_saida / "memoria_comparacao.png", dpi=120)
    plt.close(fig)

    # Grafico Fila sobreposto
    fig, ax = plt.subplots(figsize=(8.0, 4.2))
    ta = [float(a["t_s"]) for a in am_a if a.get("queue_size", "") != ""]
    qa = [int(float(a["queue_size"])) for a in am_a if a.get("queue_size", "") != ""]
    tb = [float(a["t_s"]) for a in am_b if a.get("queue_size", "") != ""]
    qb = [int(float(a["queue_size"])) for a in am_b if a.get("queue_size", "") != ""]
    ax.step(ta, qa, where="post", linewidth=1.8, label=f"{rot_a} (media={res_a['r5_fila_media']:.2f}, max={res_a['fila_maxima']})")
    ax.step(tb, qb, where="post", linewidth=1.8, label=f"{rot_b} (media={res_b['r5_fila_media']:.2f}, max={res_b['fila_maxima']})")
    ax.set_title("R5/R6 — Comparacao do Tamanho da Fila de Reconstrucao")
    ax.set_xlabel("Tempo (s)")
    ax.set_ylabel("Imagens aguardando na fila")
    ax.grid(True, alpha=0.3)
    ax.legend(loc="best")
    fig.tight_layout()
    fig.savefig(pasta_saida / "fila_comparacao.png", dpi=120)
    plt.close(fig)

    comp = {"cenario_a": res_a, "cenario_b": res_b}
    with open(pasta_saida / "comparacao.json", "w", encoding="utf-8") as arq:
        json.dump(comp, arq, indent=2, ensure_ascii=False)

    md = f"""# Comparacao R1–R7: `{rot_a}` vs. `{rot_b}`

| Req. | Metrica | `{rot_a}` | `{rot_b}` |
|---|---|---|---|
| **R1** | Imagens reconstruidas | {res_a['r1_total_imagens']} | {res_b['r1_total_imagens']} |
| **R2** | Tempo total (s) | {res_a['r2_tempo_total_s']:.3f} s | {res_b['r2_tempo_total_s']:.3f} s |
| **R3** | CPU media / pico (%) | {res_a['cpu_proc_media_pct']:.1f}% / {res_a['cpu_proc_pico_pct']:.1f}% | {res_b['cpu_proc_media_pct']:.1f}% / {res_b['cpu_proc_pico_pct']:.1f}% |
| **R4** | Memoria RSS media / pico (MB) | {res_a['rss_media_mb']:.1f} / {res_a['rss_pico_mb']:.1f} MB | {res_b['rss_media_mb']:.1f} / {res_b['rss_pico_mb']:.1f} MB |
| **R5** | Media da fila (max) | {res_a['r5_fila_media']:.3f} (max {res_a['fila_maxima']}) | {res_b['r5_fila_media']:.3f} (max {res_b['fila_maxima']}) |
| **R6** | Moda da fila | {res_a['r6_fila_moda']} | {res_b['r6_fila_moda']} |
| **R7** | Tempo medio de reconstrucao | {res_a['r7_tempo_medio_reconstrucao_ms']:.2f} ms | {res_b['r7_tempo_medio_reconstrucao_ms']:.2f} ms |
| Extra | Tempo medio de espera na fila | {res_a['espera_media_ms']:.2f} ms | {res_b['espera_media_ms']:.2f} ms |
| Extra | Latencia p50 / p95 | {res_a['latencia_p50_ms']:.1f} / {res_a['latencia_p95_ms']:.1f} ms | {res_b['latencia_p50_ms']:.1f} / {res_b['latencia_p95_ms']:.1f} ms |
| Extra | Vazao (imagens/s) | {res_a['vazao_imagens_por_s']:.3f} img/s | {res_b['vazao_imagens_por_s']:.3f} img/s |
| Extra | Rejeicoes HTTP 503 | {res_a['rejeicoes_503']} | {res_b['rejeicoes_503']} |
"""
    with open(pasta_saida / "comparacao.md", "w", encoding="utf-8") as arq:
        arq.write(md)

    return comp


def main() -> None:
    parser = argparse.ArgumentParser(description="Gera relatorio R1-R7 unico ou comparativo.")
    parser.add_argument("pasta", nargs="?", type=Path, help="Pasta do experimento unico.")
    parser.add_argument(
        "--comparar",
        nargs=2,
        type=Path,
        metavar=("PASTA_A", "PASTA_B"),
        help="Compara dois experimentos lado a lado.",
    )
    parser.add_argument("--saida", type=Path, default=None, help="Pasta de saida no modo --comparar.")
    args = parser.parse_args()

    if args.comparar:
        pasta_a, pasta_b = args.comparar
        saida = args.saida or (pasta_a.parent / f"comp_{pasta_a.name}_vs_{pasta_b.name}")
        comp = gerar_relatorio_comparativo(pasta_a, pasta_b, saida)
        print(f"Relatorio comparativo salvo em {saida}")
        print(json.dumps(comp, indent=2, ensure_ascii=False))
    elif args.pasta:
        resumo = gerar_relatorio_unico(args.pasta)
        print(json.dumps(resumo, indent=2, ensure_ascii=False))
    else:
        parser.error("Informe uma pasta de experimento ou use --comparar PASTA_A PASTA_B.")


if __name__ == "__main__":
    main()

