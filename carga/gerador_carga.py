"""Gerador de carga multi-cliente com aplicacao de ganho e retry/backoff no HTTP 503."""

import argparse
import json
import random
import sys
import threading
import time
from collections import defaultdict
from pathlib import Path

import numpy as np
import requests

RAIZ = Path(__file__).resolve().parents[1]
if str(RAIZ) not in sys.path:
    sys.path.insert(0, str(RAIZ))

from carga.ganho import DIMENSOES_MODELO, aplicar_ganho
from carga.sequencia import ler_sequencia_jsonl


def carregar_sinal_bruto(pasta_dados: Path, nome_sinal: str, modelo: str) -> np.ndarray:
    caminho_npy = pasta_dados / f"{nome_sinal}.npy"
    if caminho_npy.exists():
        return np.load(caminho_npy).ravel().astype(np.float32)
    S, N, _, _ = DIMENSOES_MODELO[modelo]
    caminho_bin = pasta_dados / f"{nome_sinal}.bin"
    return np.fromfile(caminho_bin, dtype=np.float32, count=S * N)


def executar_carga(
    url_base: str,
    itens_sequencia: list[dict],
    pasta_dados: Path = RAIZ / "data",
    caminho_respostas: Path | None = None,
    max_tentativas: int = 15,
    backoff_inicial: float = 0.5,
    salvar_f: bool = False,
    timeout_leitura: float = 600.0,
) -> dict:
    # Pre-carrega os sinais brutos em memoria (o ganho e calculado por cada cliente no envio)
    sinais_brutos: dict[str, np.ndarray] = {}
    for item in itens_sequencia:
        nome = item["signal_file"]
        if nome not in sinais_brutos:
            sinais_brutos[nome] = carregar_sinal_bruto(pasta_dados, nome, item["model"])

    por_cliente: dict[str, list[dict]] = defaultdict(list)
    for item in itens_sequencia:
        por_cliente[item["client_id"]].append(item)

    trava = threading.Lock()
    respostas_registradas: list[dict] = []
    contadores = {
        "enviados": len(itens_sequencia),
        "sucesso_200": 0,
        "rejeicoes_503": 0,
        "erros_finais": 0,
    }

    url_reconstruir = f"{url_base.rstrip('/')}/reconstruir"

    def rotina_cliente( _, envios: list[dict]) -> None:
        sessao = requests.Session()
        for item in envios:
            atraso = float(item.get("delay_s", 0.0))
            if atraso > 0:
                time.sleep(atraso)

            modelo = item["model"]
            S, N, _, _ = DIMENSOES_MODELO[modelo]
            g_ganho = aplicar_ganho(sinais_brutos[item["signal_file"]], S, N)
            payload = {
                "client_id": item["client_id"],
                "signal_id": item["signal_id"],
                "model": modelo,
                "algorithm": item["algorithm"],
                "g": g_ganho.tolist(),
            }

            t_inicio_cliente = time.perf_counter()
            tentativas_503_item = 0
            sucesso = False
            status_final = 0
            corpo_resp = {}

            for tentativa in range(max_tentativas):
                try:
                    resp = sessao.post(url_reconstruir, json=payload, timeout=timeout_leitura)
                    status_final = resp.status_code
                    if resp.status_code == 200:
                        corpo_resp = resp.json()
                        sucesso = True
                        break
                    if resp.status_code == 503:
                        tentativas_503_item += 1
                        with trava:
                            contadores["rejeicoes_503"] += 1
                        if tentativa + 1 >= max_tentativas:
                            break
                        retry_hdr = float(resp.headers.get("Retry-After", backoff_inicial))
                        jitter = random.uniform(0.0, 0.25)
                        espera = min(4.0, max(backoff_inicial, retry_hdr * 0.5) * (1.5 ** min(tentativa, 5))) + jitter
                        time.sleep(espera)
                        continue
                    corpo_resp = {"erro_status": resp.status_code, "texto": resp.text}
                    break
                except Exception as exc:
                    corpo_resp = {"excecao": str(exc)}
                    break

            latencia_cliente_ms = (time.perf_counter() - t_inicio_cliente) * 1000.0
            registro = {
                "client_id": item["client_id"],
                "signal_id": item["signal_id"],
                "signal_file": item["signal_file"],
                "model": modelo,
                "algorithm": item["algorithm"],
                "status_code": status_final,
                "tentativas_503": tentativas_503_item,
                "latencia_cliente_ms": round(latencia_cliente_ms, 3),
            }
            if sucesso:
                f_lista = corpo_resp.get("f", [])
                f_arr = np.asarray(f_lista, dtype=np.float32)
                registro.update({
                    "started_at": corpo_resp.get("started_at"),
                    "finished_at": corpo_resp.get("finished_at"),
                    "iterations": corpo_resp.get("iterations"),
                    "duration_ms": corpo_resp.get("duration_ms"),
                    "wait_ms": corpo_resp.get("wait_ms"),
                    "error": corpo_resp.get("error"),
                    "len_f": int(f_arr.size),
                    "norma_f": float(np.linalg.norm(f_arr)) if f_arr.size else 0.0,
                })
                if salvar_f:
                    registro["f"] = f_lista
            else:
                registro["detalhe_erro"] = corpo_resp

            with trava:
                if sucesso:
                    contadores["sucesso_200"] += 1
                else:
                    contadores["erros_finais"] += 1
                respostas_registradas.append(registro)

    t0_parede = time.perf_counter()
    threads = [
        threading.Thread(target=rotina_cliente, args=(cid, envios))
        for cid, envios in sorted(por_cliente.items())
    ]
    for t in threads:
        t.start()
    for t in threads:
        t.join()
    tempo_parede_s = time.perf_counter() - t0_parede

    if caminho_respostas is not None:
        caminho_respostas.parent.mkdir(parents=True, exist_ok=True)
        with open(caminho_respostas, "w", encoding="utf-8") as arq:
            for reg in respostas_registradas:
                arq.write(json.dumps(reg, ensure_ascii=False) + "\n")

    latencias_ok = [
        r["latencia_cliente_ms"] for r in respostas_registradas if r["status_code"] == 200
    ]
    resumo = {
        **contadores,
        "clientes": len(por_cliente),
        "tempo_parede_s": round(tempo_parede_s, 4),
        "latencia_cliente_media_ms": round(float(np.mean(latencias_ok)), 3) if latencias_ok else 0.0,
        "latencia_cliente_p50_ms": round(float(np.percentile(latencias_ok, 50)), 3) if latencias_ok else 0.0,
        "latencia_cliente_p95_ms": round(float(np.percentile(latencias_ok, 95)), 3) if latencias_ok else 0.0,
    }
    return {"resumo": resumo, "respostas": respostas_registradas}


def main() -> None:
    parser = argparse.ArgumentParser(description="Executa carga de clientes contra o servidor HTTP.")
    parser.add_argument("--url", type=str, default="http://127.0.0.1:8080")
    parser.add_argument("--sequencia", type=Path, required=True)
    parser.add_argument("--pasta-dados", type=Path, default=RAIZ / "data")
    parser.add_argument("--saida", type=Path, default=None)
    parser.add_argument("--max-tentativas", type=int, default=7)
    parser.add_argument("--backoff-inicial", type=float, default=0.5)
    parser.add_argument("--salvar-f", action="store_true")
    args = parser.parse_args()

    itens = ler_sequencia_jsonl(args.sequencia)
    resultado = executar_carga(
        url_base=args.url,
        itens_sequencia=itens,
        pasta_dados=args.pasta_dados,
        caminho_respostas=args.saida,
        max_tentativas=args.max_tentativas,
        backoff_inicial=args.backoff_inicial,
        salvar_f=args.salvar_f,
    )
    print(json.dumps(resultado["resumo"], indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
