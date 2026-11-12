"""Camada HTTP e workers de reconstrução."""

from __future__ import annotations

import json
import queue
import signal
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Any

from servers.python.algoritmos import cgne, cgnr
from servers.python.config import Config
from servers.python.fila import Estatisticas, FilaJobs, Job, Resposta
from servers.python.logging_csv import abrir_log, fechar_log, registrar_log
from servers.python.modelos import Modelo
from servers.python.protocolo import interpretar_pedido, para_json
from utilitarios import agora_iso, diferenca_ms


class ServidorHTTP(ThreadingHTTPServer):
    daemon_threads = True

    def __init__(self, endereco: tuple[str, int],
                 handler: type[BaseHTTPRequestHandler],
                 max_threads: int) -> None:
        super().__init__(endereco, handler)
        self._slots_http = threading.BoundedSemaphore(max_threads)

    def process_request_thread(self, request: Any, client_address: Any) -> None:
        with self._slots_http:
            super().process_request_thread(request, client_address)


def iniciar_servidor(config: Config, modelos: dict[str, Modelo]) -> None:
    fila = FilaJobs(config.max_fila)
    estatisticas = Estatisticas()
    estatisticas_lock = threading.Lock()
    arquivo_log = abrir_log(config.pasta_logs)
    log_lock = threading.Lock()
    parando = threading.Event()

    def trabalhador() -> None:
        while True:
            job = fila.retirar()
            if job is None:
                return
            with estatisticas_lock:
                estatisticas.em_processamento += 1
            try:
                modelo = modelos[job.pedido.model]
                inicio = time.perf_counter()
                if job.pedido.algorithm == "CGNE":
                    vetor, iteracoes, erro = cgne(modelo.matriz, job.pedido.g)
                else:
                    vetor, iteracoes, erro = cgnr(modelo.matriz, job.pedido.g)
                fim = time.perf_counter()
                resposta = Resposta(
                    job.pedido.client_id, job.pedido.signal_id, job.pedido.algorithm,
                    job.pedido.model, agora_iso(), agora_iso(), job.pedido.recebido_at,
                    iteracoes, diferenca_ms(inicio, fim),
                    diferenca_ms(job.pedido.recebido_em, inicio), erro, vetor)
                registrar_log(arquivo_log, resposta, log_lock)
                job.resultado.put((resposta, None))
            except Exception as exc:
                job.resultado.put((None, exc))
            finally:
                with estatisticas_lock:
                    estatisticas.em_processamento -= 1
                    estatisticas.processados += 1

    trabalhadores = [threading.Thread(target=trabalhador, daemon=True)
                      for _ in range(config.workers)]
    for trabalhador_thread in trabalhadores:
        trabalhador_thread.start()

    def responder_json(handler: BaseHTTPRequestHandler, status: int,
                       corpo: dict[str, Any], retry: bool = False) -> None:
        dados = json.dumps(corpo, ensure_ascii=False).encode("utf-8")
        handler.send_response(status)
        handler.send_header("Content-Type", "application/json; charset=utf-8")
        handler.send_header("Content-Length", str(len(dados)))
        if retry:
            handler.send_header("Retry-After", "1")
        handler.end_headers()
        handler.wfile.write(dados)

    class Handler(BaseHTTPRequestHandler):

        def do_GET(self) -> None:
            if self.path != "/status":
                responder_json(self, 404, {"erro": "rota nao encontrada"})
                return
            with estatisticas_lock:
                status = {
                    "queue_size": fila.tamanho(),
                    "workers": config.workers,
                    "processed": estatisticas.processados,
                    "in_progress": estatisticas.em_processamento,
                    "rejected": estatisticas.rejeitados,
                    "max_queue": config.max_fila,
                }
            responder_json(self, 200, status)

        def do_POST(self) -> None:
            if self.path != "/reconstruir":
                responder_json(self, 404, {"erro": "rota nao encontrada"})
                return
            try:
                tamanho = int(self.headers.get("Content-Length", ""))
                if tamanho < 0:
                    raise ValueError
                pedido = interpretar_pedido(self.rfile.read(tamanho), modelos)
            except (TypeError, ValueError) as exc:
                responder_json(self, 400, {"erro": str(exc)})
                return

            job = Job(pedido, queue.Queue(maxsize=1))
            if not fila.inserir(job):
                with estatisticas_lock:
                    estatisticas.rejeitados += 1
                responder_json(self, 503, {"erro": "fila cheia"}, retry=True)
                return

            resposta, erro = job.resultado.get()
            if erro is not None:
                responder_json(self, 500, {"erro": str(erro)})
            else:
                assert resposta is not None
                responder_json(self, 200, para_json(resposta))

        def log_message(self, _format: str, *_args: Any) -> None:
            del _format, _args
            return

    servidor = ServidorHTTP(("0.0.0.0", config.porta), Handler, config.threads_http)

    def solicitar_parada(_sig: int, _frame: Any) -> None:
        del _sig, _frame
        if not parando.is_set():
            parando.set()
            threading.Thread(target=servidor.shutdown, daemon=True).start()

    signal.signal(signal.SIGINT, solicitar_parada)
    signal.signal(signal.SIGTERM, solicitar_parada)
    print(f"[Servidor Python] Escutando em http://0.0.0.0:{config.porta} | "
          f"workers={config.workers} | max_queue={config.max_fila} | "
          f"http_threads={config.threads_http}")
    try:
        servidor.serve_forever()
    finally:
        servidor.server_close()
        fila.fechar()
        for trabalhador_thread in trabalhadores:
            trabalhador_thread.join()
        fechar_log(arquivo_log, log_lock)
        print(f"[Servidor Python] Encerrado com sucesso. Total processados: "
              f"{estatisticas.processados}")
