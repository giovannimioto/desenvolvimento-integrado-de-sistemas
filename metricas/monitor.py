"""Coletor de metricas de CPU, memoria (psutil, incluindo filhos) e fila (GET /status)."""

import argparse
import csv
import shlex
import signal
import subprocess
import time
from pathlib import Path

import psutil
import requests


def coletar_arvore_processos(
    pid_raiz: int, cache_procs: dict[int, psutil.Process]
) -> tuple[float, float, int]:
    """Soma cpu_percent, rss_mb e num_threads do processo raiz e de todos os seus filhos."""
    try:
        if pid_raiz not in cache_procs:
            p_raiz = psutil.Process(pid_raiz)
            p_raiz.cpu_percent(interval=None)
            cache_procs[pid_raiz] = p_raiz
        else:
            p_raiz = cache_procs[pid_raiz]
        filhos = p_raiz.children(recursive=True)
    except (psutil.NoSuchProcess, psutil.AccessDenied):
        return 0.0, 0.0, 0

    todos = [p_raiz] + filhos
    pids_ativos = set()
    cpu_total = 0.0
    rss_bytes = 0
    threads_total = 0

    for p in todos:
        try:
            pid = p.pid
            pids_ativos.add(pid)
            if pid not in cache_procs:
                p.cpu_percent(interval=None)
                cache_procs[pid] = p
            proc_ref = cache_procs[pid]
            cpu_total += proc_ref.cpu_percent(interval=None)
            rss_bytes += proc_ref.memory_info().rss
            threads_total += proc_ref.num_threads()
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            continue

    for pid_antigo in list(cache_procs.keys()):
        if pid_antigo not in pids_ativos:
            cache_procs.pop(pid_antigo, None)

    return cpu_total, rss_bytes / (1024.0 * 1024.0), threads_total


def main() -> None:
    parser = argparse.ArgumentParser(description="Monitora CPU/RAM (psutil) e fila (/status).")
    grupo = parser.add_mutually_exclusive_group(required=True)
    grupo.add_argument("--pid", type=int, help="PID do servidor em execucao.")
    grupo.add_argument("--cmd", type=str, help="Comando para iniciar o servidor.")
    parser.add_argument("--url", type=str, default="http://127.0.0.1:8080")
    parser.add_argument("--intervalo", type=float, default=0.5)
    parser.add_argument("--duracao", type=float, default=0.0, help="0 = ate encerrar o processo/sinal")
    parser.add_argument("--saida", type=Path, required=True)
    args = parser.parse_args()

    proc_iniciado = None
    if args.cmd:
        proc_iniciado = subprocess.Popen(shlex.split(args.cmd))
        pid_alvo = proc_iniciado.pid
    else:
        pid_alvo = args.pid

    parar = False

    def tratar_sinal(_sig, _frame):
        nonlocal parar
        parar = True

    signal.signal(signal.SIGINT, tratar_sinal)
    signal.signal(signal.SIGTERM, tratar_sinal)

    args.saida.parent.mkdir(parents=True, exist_ok=True)
    cache_procs: dict[int, psutil.Process] = {}
    psutil.cpu_percent(interval=None)
    coletar_arvore_processos(pid_alvo, cache_procs)

    url_status = f"{args.url.rstrip('/')}/status"
    sessao = requests.Session()
    t0 = time.perf_counter()

    try:
        with open(args.saida, "w", newline="", encoding="utf-8") as arq_csv:
            escritor = csv.writer(arq_csv)
            escritor.writerow([
                "t_s",
                "cpu_proc_pct",
                "cpu_sistema_pct",
                "rss_mb",
                "threads",
                "queue_size",
                "in_progress",
                "processed",
            ])
            arq_csv.flush()

            while not parar:
                if not psutil.pid_exists(pid_alvo):
                    break

                time.sleep(args.intervalo)
                if parar or not psutil.pid_exists(pid_alvo):
                    break

                t_s = time.perf_counter() - t0
                cpu_proc, rss_mb, n_threads = coletar_arvore_processos(pid_alvo, cache_procs)
                cpu_sis = psutil.cpu_percent(interval=None)

                q_size: int | str = ""
                in_prog: int | str = ""
                proc_cnt: int | str = ""
                try:
                    r = sessao.get(url_status, timeout=0.3)
                    if r.status_code == 200:
                        dados = r.json()
                        q_size = dados.get("queue_size", "")
                        in_prog = dados.get("in_progress", "")
                        proc_cnt = dados.get("processed", "")
                except Exception:
                    pass

                escritor.writerow([
                    f"{t_s:.3f}",
                    f"{cpu_proc:.2f}",
                    f"{cpu_sis:.2f}",
                    f"{rss_mb:.2f}",
                    n_threads,
                    q_size,
                    in_prog,
                    proc_cnt,
                ])
                arq_csv.flush()

                if args.duracao > 0 and t_s >= args.duracao:
                    break
    finally:
        if proc_iniciado is not None and proc_iniciado.poll() is None:
            proc_iniciado.terminate()
            try:
                proc_iniciado.wait(timeout=5)
            except subprocess.TimeoutExpired:
                proc_iniciado.kill()


if __name__ == "__main__":
    main()

