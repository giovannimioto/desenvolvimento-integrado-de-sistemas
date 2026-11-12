"""Coleta CPU, memória, processos filhos e tamanho da fila."""

import argparse
import csv
import shlex
import signal
import subprocess
import time
from pathlib import Path

import psutil
import requests


def coletar_arvore(pid_raiz: int, cache: dict[int, psutil.Process]) -> tuple[float, float, int]:
    try:
        raiz = cache.setdefault(pid_raiz, psutil.Process(pid_raiz))
        filhos = raiz.children(recursive=True)
    except (psutil.NoSuchProcess, psutil.AccessDenied):
        return 0.0, 0.0, 0

    ativos, cpu, memoria, threads = set(), 0.0, 0, 0
    for processo in [raiz, *filhos]:
        try:
            ativos.add(processo.pid)
            ref = cache.setdefault(processo.pid, processo)
            cpu += ref.cpu_percent(interval=None)
            memoria += ref.memory_info().rss
            threads += ref.num_threads()
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            continue
    for pid in set(cache) - ativos:
        cache.pop(pid)
    return cpu, memoria / 1024**2, threads


def ler_fila(sessao: requests.Session, url: str) -> tuple[int | str, int | str, int | str]:
    try:
        resposta = sessao.get(url, timeout=0.3)
        if resposta.status_code == 200:
            dados = resposta.json()
            return tuple(dados.get(chave, "") for chave in ("queue_size", "in_progress", "processed"))
    except requests.RequestException:
        pass
    return "", "", ""


def argumentos() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Monitora CPU/RAM e fila (/status).")
    grupo = parser.add_mutually_exclusive_group(required=True)
    grupo.add_argument("--pid", type=int)
    grupo.add_argument("--cmd", type=str)
    parser.add_argument("--url", default="http://127.0.0.1:8080")
    parser.add_argument("--intervalo", type=float, default=0.5)
    parser.add_argument("--duracao", type=float, default=0.0)
    parser.add_argument("--saida", type=Path, required=True)
    return parser.parse_args()


def main() -> None:
    args = argumentos()
    iniciado = subprocess.Popen(shlex.split(args.cmd)) if args.cmd else None
    pid = iniciado.pid if iniciado else args.pid
    parar = False

    def sinalizar(_sig, _frame):
        nonlocal parar
        parar = True

    signal.signal(signal.SIGINT, sinalizar)
    signal.signal(signal.SIGTERM, sinalizar)
    args.saida.parent.mkdir(parents=True, exist_ok=True)
    cache: dict[int, psutil.Process] = {}
    psutil.cpu_percent(interval=None)
    coletar_arvore(pid, cache)
    inicio = time.perf_counter()
    sessao = requests.Session()
    cabecalho = ["t_s", "cpu_proc_pct", "cpu_sistema_pct", "rss_mb", "threads",
                 "queue_size", "in_progress", "processed"]
    try:
        with args.saida.open("w", newline="", encoding="utf-8") as arquivo:
            escritor = csv.writer(arquivo)
            escritor.writerow(cabecalho)
            while not parar and psutil.pid_exists(pid):
                time.sleep(args.intervalo)
                if parar or not psutil.pid_exists(pid):
                    break
                tempo = time.perf_counter() - inicio
                cpu, rss, threads = coletar_arvore(pid, cache)
                fila = ler_fila(sessao, f"{args.url.rstrip('/')}/status")
                escritor.writerow([f"{tempo:.3f}", f"{cpu:.2f}", f"{psutil.cpu_percent():.2f}",
                                   f"{rss:.2f}", threads, *fila])
                arquivo.flush()
                if args.duracao > 0 and tempo >= args.duracao:
                    break
    finally:
        if iniciado and iniciado.poll() is None:
            iniciado.terminate()
            try:
                iniciado.wait(timeout=5)
            except subprocess.TimeoutExpired:
                iniciado.kill()


if __name__ == "__main__":
    main()
