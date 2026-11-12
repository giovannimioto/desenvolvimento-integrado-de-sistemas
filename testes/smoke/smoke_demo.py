"""Smoke test portável para ensaio e apresentação do servidor C++."""

import argparse
import subprocess
import sys
import socket
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[2]
if str(RAIZ) not in sys.path:
    sys.path.insert(0, str(RAIZ))

from testes.smoke.verificacoes import (
    aguardar_status,
    testar_cargas,
    testar_reconstrucoes,
    verificar_dados,
)

DATA = RAIZ / "data"
PASTA_REF = DATA / "referencias"
BIN_SERVIDOR = RAIZ / "servers" / "cpp" / "build" / "servidor"


def escolher_porta_livre() -> int:
    with socket.socket() as sock:
        sock.bind(("127.0.0.1", 0))
        return int(sock.getsockname()[1])


def registrar(etapas: list, nome: str, ok: bool, detalhe: str) -> None:
    etapas.append((nome, ok, detalhe))
    print(f"[{'PASS' if ok else 'FAIL'}] {nome:38s} | {detalhe}")


def iniciar_servidor(perfil: str, pasta: Path) -> tuple[str, subprocess.Popen]:
    porta = escolher_porta_livre()
    workers = 2 if perfil == "demo" else 4
    fila = 4 if perfil == "demo" else 8
    comando = [
        str(BIN_SERVIDOR), "--port", str(porta), "--workers", str(workers),
        "--max-queue", str(fila), "--modelos", "30x30,60x60",
        "--data-dir", str(DATA), "--log-dir", str(pasta / "logs"),
    ]
    processo = subprocess.Popen(comando, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
    return f"http://127.0.0.1:{porta}", processo


def main() -> None:
    parser = argparse.ArgumentParser(description="Smoke test rapido do servidor C++.")
    parser.add_argument("--perfil", choices=["demo", "benchmark"], default="demo")
    parser.add_argument("--url", default=None, help="Usa servidor ja em execucao.")
    args = parser.parse_args()
    workers = 2 if args.perfil == "demo" else 4
    max_queue = 4 if args.perfil == "demo" else 8
    etapas, processo = [], None
    pasta = RAIZ / "resultados" / f"smoke_{args.perfil}"
    pasta.mkdir(parents=True, exist_ok=True)

    ok, detalhe = verificar_dados(DATA)
    registrar(etapas, "1. Dados .bin e RAM disponivel", ok, detalhe)
    if not ok:
        sys.exit(1)
    if args.url:
        url = args.url.rstrip("/")
    else:
        url, processo = iniciar_servidor(args.perfil, pasta)
    try:
        ok, status, boot = aguardar_status(url)
        registrar(etapas, "2/3. Subida do servidor e GET /status", ok,
                  f"workers={status.get('workers')}, max_queue={status.get('max_queue')}, tempo_boot={boot:.2f}s")
        if not ok:
            sys.exit(1)
        tempos, reconstrucoes = testar_reconstrucoes(url, DATA, PASTA_REF, pasta)
        for etapa in reconstrucoes:
            registrar(etapas, *etapa)
        for etapa in testar_cargas(url, DATA, workers, max_queue):
            registrar(etapas, *etapa)
    finally:
        if processo is not None:
            processo.terminate()
            try:
                processo.wait(timeout=10)
            except subprocess.TimeoutExpired:
                processo.kill()
            registrar(etapas, "7. Encerramento limpo (SIGTERM)", processo.returncode == 0,
                      f"exit_code={processo.returncode}")

    print(f"\n=== Resumo Smoke Test ({args.perfil}) ===")
    for modelo, tempo in tempos.items():
        print(f" - Tempo medio {modelo}: {tempo:.1f} ms")
    falhas = [nome for nome, ok, _ in etapas if not ok]
    if falhas:
        print("RESULTADO FINAL: FAIL ->", ", ".join(falhas))
        sys.exit(1)
    print("RESULTADO FINAL: PASS (100% das etapas aprovadas)")


if __name__ == "__main__":
    main()
