"""Gera métricas R1-R7, gráficos e comparação entre experimentos."""

import argparse
import json
import sys
from collections import Counter
from datetime import datetime
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import numpy as np
import psutil

RAIZ = Path(__file__).resolve().parents[1]
if str(RAIZ) not in sys.path:
    sys.path.insert(0, str(RAIZ))

from utilitarios import ler_csv, salvar_grafico, salvar_json


def ler_reconstrucoes(pasta: Path) -> list[dict]:
    arquivos = sorted(pasta.glob("reconstrucoes*.csv"))
    return ler_csv(arquivos[-1]) if arquivos else []


def ler_amostras(pasta: Path) -> list[dict]:
    return ler_csv(pasta / "amostras.csv")


def moda(valores: list[int]) -> int:
    if not valores:
        return 0
    frequencias = Counter(valores)
    maior = max(frequencias.values())
    return min(valor for valor, frequencia in frequencias.items() if frequencia == maior)


def serie(amostras: list[dict], chave: str, tipo=float) -> tuple[list[float], list]:
    validas = [a for a in amostras if a.get(chave, "") != ""]
    return [float(a["t_s"]) for a in validas], [tipo(a[chave]) for a in validas]


def graficos(pasta: Path, amostras: list[dict], resumo: dict) -> None:
    tempo, cpu = serie(amostras, "cpu_proc_pct")
    _, cpu_sistema = serie(amostras, "cpu_sistema_pct")
    _, memoria = serie(amostras, "rss_mb")
    if not tempo:
        tempo, cpu, cpu_sistema, memoria = [0.0, 1.0], [0.0, 0.0], [0.0, 0.0], [0.0, 0.0]
    n_cpus = psutil.cpu_count(logical=True) or 1
    salvar_grafico(
        pasta, "cpu.png",
        [(tempo, cpu, "Servidor (% psutil)"),
         (tempo, [valor / n_cpus for valor in cpu], f"Normalizado ({n_cpus} threads)"),
         (tempo, cpu_sistema, "CPU Sistema Total (%)")],
        f"R3 — Consumo de CPU ({pasta.name})", "CPU (%)",
    )
    salvar_grafico(
        pasta, "memoria.png",
        [(tempo, memoria, "RSS Servidor (MB)")],
        f"R4 — Consumo de Memoria RSS ({pasta.name})", "Memoria RSS (MB)",
    )
    tempo_fila, fila = serie(amostras, "queue_size", lambda x: int(float(x)))
    _, processando = serie(amostras, "in_progress", lambda x: int(float(x)))
    if not tempo_fila:
        tempo_fila, fila, processando = [0.0, 1.0], [0, 0], [0, 0]
    salvar_grafico(
        pasta, "fila.png",
        [(tempo_fila, fila, "Aguardando na fila"),
         (tempo_fila, processando, "Em processamento")],
        f"R5/R6 — Fila (media={resumo['r5_fila_media']:.2f}, moda={resumo['r6_fila_moda']})",
        "Numero de imagens", degrau=True,
    )


def gerar_relatorio_unico(pasta: Path) -> dict:
    reconstrucoes, amostras = ler_reconstrucoes(pasta), ler_amostras(pasta)
    meta = {}
    if (pasta / "meta.json").exists():
        with (pasta / "meta.json").open(encoding="utf-8") as arquivo:
            meta = json.load(arquivo)

    duracoes = [float(r["duration_ms"]) for r in reconstrucoes if r.get("duration_ms")]
    esperas = [float(r["wait_ms"]) for r in reconstrucoes if r.get("wait_ms")]
    latencias = [d + e for d, e in zip(duracoes, esperas)]
    try:
        inicio = [datetime.fromisoformat(r.get("received_at") or r["started_at"]) for r in reconstrucoes]
        fim = [datetime.fromisoformat(r["finished_at"]) for r in reconstrucoes]
        tempo_total = max(0.001, (max(fim) - min(inicio)).total_seconds()) if inicio else 0.0
    except (KeyError, TypeError, ValueError):
        tempo_total = float(meta.get("tempo_parede_s", 0.0))
    tempo_total = tempo_total or float(meta.get("tempo_parede_s", 0.0))

    filas = [int(float(a["queue_size"])) for a in amostras if a.get("queue_size", "") != ""]
    cpu = [float(a["cpu_proc_pct"]) for a in amostras] or [0.0]
    memoria = [float(a["rss_mb"]) for a in amostras] or [0.0]
    por_modelo = {
        modelo: [float(r["duration_ms"]) for r in reconstrucoes if r.get("model") == modelo]
        for modelo in ("30x30", "60x60")
    }
    resumo = {
        "experimento": pasta.name, "servidor": meta.get("servidor", "cpp"),
        "workers": meta.get("workers"), "max_queue": meta.get("max_queue"),
        "r1_total_imagens": len(reconstrucoes), "r2_tempo_total_s": round(tempo_total, 4),
        "r2_tempo_parede_s": round(float(meta.get("tempo_parede_s", tempo_total)), 4),
        "r3_grafico_cpu": "cpu.png", "r4_grafico_memoria": "memoria.png",
        "r5_fila_media": round(float(np.mean(filas)) if filas else 0.0, 4),
        "r6_fila_moda": moda(filas), "r7_tempo_medio_reconstrucao_ms": round(float(np.mean(duracoes)) if duracoes else 0.0, 3),
        "r7_tempo_medio_reconstrucao_s": round(float(np.mean(duracoes)) / 1000 if duracoes else 0.0, 4),
        "fila_maxima": max(filas, default=0), "espera_media_ms": round(float(np.mean(esperas)) if esperas else 0.0, 3),
        "latencia_p50_ms": round(float(np.percentile(latencias, 50)) if latencias else 0.0, 3),
        "latencia_p95_ms": round(float(np.percentile(latencias, 95)) if latencias else 0.0, 3),
        "tempo_medio_30x30_ms": round(float(np.mean(por_modelo["30x30"])) if por_modelo["30x30"] else 0.0, 3),
        "tempo_medio_60x60_ms": round(float(np.mean(por_modelo["60x60"])) if por_modelo["60x60"] else 0.0, 3),
        "cpu_proc_media_pct": round(float(np.mean(cpu)), 2), "cpu_proc_pico_pct": round(float(np.max(cpu)), 2),
        "rss_media_mb": round(float(np.mean(memoria)), 2), "rss_pico_mb": round(float(np.max(memoria)), 2),
        "vazao_imagens_por_s": round(len(reconstrucoes) / tempo_total, 3) if tempo_total else 0.0,
        "rejeicoes_503": int(meta.get("rejeicoes_503", 0)), "amostras_coletadas": len(amostras),
        "falhas_status": sum(a.get("queue_size", "") == "" for a in amostras),
    }
    graficos(pasta, amostras, resumo)
    salvar_json(pasta / "resumo.json", resumo)
    (pasta / "resumo.md").write_text(_markdown_unico(resumo), encoding="utf-8")
    return resumo


def _markdown_unico(r: dict) -> str:
    return f"""# Relatorio de Metricas R1–R7: `{r['experimento']}`

| Requisito | Metrica | Valor |
|---|---|---|
| **R1** | Imagens reconstruidas | **{r['r1_total_imagens']}** |
| **R2** | Tempo total | **{r['r2_tempo_total_s']:.3f} s** |
| **R3** | CPU media / pico | **{r['cpu_proc_media_pct']:.1f}% / {r['cpu_proc_pico_pct']:.1f}%** |
| **R4** | Memoria RSS media / pico | **{r['rss_media_mb']:.1f} / {r['rss_pico_mb']:.1f} MB** |
| **R5** | Fila media (max) | **{r['r5_fila_media']:.3f} ({r['fila_maxima']})** |
| **R6** | Moda da fila | **{r['r6_fila_moda']}** |
| **R7** | Reconstrucao media | **{r['r7_tempo_medio_reconstrucao_ms']:.2f} ms** |

- Vazao: `{r['vazao_imagens_por_s']:.3f}` imagens/s
- Espera media: `{r['espera_media_ms']:.2f}` ms
- Latencia p50 / p95: `{r['latencia_p50_ms']:.1f}` / `{r['latencia_p95_ms']:.1f}` ms
- Rejeicoes HTTP 503: `{r['rejeicoes_503']}`
"""


def gerar_relatorio_comparativo(pasta_a: Path, pasta_b: Path, pasta_saida: Path) -> dict:
    a, b = gerar_relatorio_unico(pasta_a), gerar_relatorio_unico(pasta_b)
    am_a, am_b = ler_amostras(pasta_a), ler_amostras(pasta_b)
    pasta_saida.mkdir(parents=True, exist_ok=True)
    rotulos = (a["experimento"], b["experimento"])
    for nome, chave, titulo, ylabel, degrau in (
        ("cpu_comparacao.png", "cpu_proc_pct", "R3 — Comparacao de CPU", "CPU Processo (%)", False),
        ("memoria_comparacao.png", "rss_mb", "R4 — Comparacao de Memoria", "Memoria RSS (MB)", False),
        ("fila_comparacao.png", "queue_size", "R5/R6 — Comparacao da Fila", "Imagens na fila", True),
    ):
        series = []
        for dados, resumo, rotulo in ((am_a, a, rotulos[0]), (am_b, b, rotulos[1])):
            tempos, valores = serie(dados, chave, lambda x: int(float(x)) if degrau else float(x))
            series.append((tempos, valores, rotulo))
        salvar_grafico(pasta_saida, nome, series, titulo, ylabel, degrau)
    comparacao = {"cenario_a": a, "cenario_b": b}
    salvar_json(pasta_saida / "comparacao.json", comparacao)
    (pasta_saida / "comparacao.md").write_text(_markdown_comparativo(a, b), encoding="utf-8")
    return comparacao


def _markdown_comparativo(a: dict, b: dict) -> str:
    linhas = ["# Comparacao R1–R7", "", "| Metrica | A | B |", "|---|---:|---:|"]
    for nome, chave, formato in (
        ("Imagens", "r1_total_imagens", "{}"), ("Tempo total (s)", "r2_tempo_total_s", "{:.3f}"),
        ("CPU media (%)", "cpu_proc_media_pct", "{:.1f}"), ("RSS pico (MB)", "rss_pico_mb", "{:.1f}"),
        ("Fila media", "r5_fila_media", "{:.3f}"), ("Fila moda", "r6_fila_moda", "{}"),
        ("Reconstrucao media (ms)", "r7_tempo_medio_reconstrucao_ms", "{:.2f}"),
        ("Vazao (imagens/s)", "vazao_imagens_por_s", "{:.3f}"),
    ):
        linhas.append(f"| {nome} | {formato.format(a[chave])} | {formato.format(b[chave])} |")
    return "\n".join(linhas) + "\n"


def main() -> None:
    parser = argparse.ArgumentParser(description="Gera relatorio R1-R7.")
    parser.add_argument("pasta", nargs="?", type=Path)
    parser.add_argument("--comparar", nargs=2, type=Path, metavar=("PASTA_A", "PASTA_B"))
    parser.add_argument("--saida", type=Path)
    args = parser.parse_args()
    if args.comparar:
        saida = args.saida or args.comparar[0].parent / f"comp_{args.comparar[0].name}_vs_{args.comparar[1].name}"
        print(json.dumps(gerar_relatorio_comparativo(*args.comparar, saida), indent=2, ensure_ascii=False))
    elif args.pasta:
        print(json.dumps(gerar_relatorio_unico(args.pasta), indent=2, ensure_ascii=False))
    else:
        parser.error("Informe uma pasta ou use --comparar PASTA_A PASTA_B.")


if __name__ == "__main__":
    main()
