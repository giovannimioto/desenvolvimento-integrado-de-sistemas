"""Cliente concorrente para enviar sinais e gerar o relatório da execução."""

from __future__ import annotations

import argparse
import json
import sys
from collections import Counter
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

RAIZ = Path(__file__).resolve().parents[1]
if str(RAIZ) not in sys.path:
    sys.path.insert(0, str(RAIZ))

from carga.gerador_carga import executar_carga
from carga.sequencia import (
    gerar_sequencia,
    ler_sequencia_jsonl,
    salvar_sequencia_jsonl,
)
from utilitarios import DIMENSOES_MODELO


def ler_argumentos() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Executa clientes concorrentes contra um servidor de reconstrução.",
    )
    parser.add_argument("--url", default="http://127.0.0.1:8080")
    parser.add_argument("--pasta-dados", type=Path, default=RAIZ / "data")
    parser.add_argument("--saida", type=Path, default=RAIZ / "resultados" / "cliente")
    parser.add_argument("--sequencia", type=Path, default=None)
    parser.add_argument("--clientes", type=int, default=3)
    parser.add_argument("--sinais", type=int, default=15)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--intervalo", type=float, nargs=2, default=[0.5, 2.0])
    parser.add_argument("--max-tentativas", type=int, default=7)
    parser.add_argument("--backoff-inicial", type=float, default=0.5)
    parser.add_argument("--threads-clientes", type=int, default=None)
    return parser.parse_args()


def preparar_sequencia(args: argparse.Namespace, caminho: Path) -> list[dict]:
    if args.sequencia is not None:
        itens = ler_sequencia_jsonl(args.sequencia)
    else:
        itens = gerar_sequencia(
            clientes=max(3, args.clientes),
            sinais_por_cliente=max(15, args.sinais),
            seed=args.seed,
            intervalo_min=args.intervalo[0],
            intervalo_max=args.intervalo[1],
            modelos=["30x30", "60x60"],
            algoritmos=["CGNE", "CGNR"],
        )

    clientes = Counter(item["client_id"] for item in itens)
    if len(clientes) < 3 or any(total < 15 for total in clientes.values()):
        raise ValueError("a sequencia precisa ter pelo menos 3 clientes com 15 sinais cada")
    salvar_sequencia_jsonl(itens, caminho)
    return itens


def salvar_imagem(resposta: dict, destino: Path) -> None:
    modelo = resposta["model"]
    _, _, lado, _ = DIMENSOES_MODELO[modelo]
    vetor = np.asarray(resposta["f"], dtype=np.float32)
    imagem = np.abs(vetor.reshape(lado, lado, order="F"))

    figura, eixo = plt.subplots(figsize=(4, 4))
    eixo.imshow(imagem, cmap="gray")
    eixo.set_title(
        f"{resposta['client_id']} / {resposta['signal_id']} - "
        f"{modelo} {resposta['algorithm']}\n"
        f"inicio: {resposta['started_at']}\n"
        f"fim: {resposta['finished_at']}\n"
        f"iteracoes: {resposta['iterations']}",
        fontsize=8,
    )
    eixo.axis("off")
    figura.tight_layout()
    figura.savefig(destino, dpi=120)
    plt.close(figura)


def salvar_markdown(respostas: list[dict], destino: Path) -> None:
    linhas = [
        "# Relatorio de imagens reconstruidas",
        "",
        "| Imagem | Cliente | Sinal | Modelo | Algoritmo | Inicio | Termino | Iteracoes |",
        "|---|---|---|---|---|---|---|---|",
    ]
    for r in respostas:
        if r["status_code"] == 200:
            linhas.append(
                f"| ![]({r['imagem']}) | {r['client_id']} | {r['signal_id']} | "
                f"{r['model']} | {r['algorithm']} | {r['started_at']} | "
                f"{r['finished_at']} | {r['iterations']} |"
            )
    destino.write_text("\n".join(linhas) + "\n", encoding="utf-8")


def gerar_relatorio(resultado: dict, pasta_saida: Path) -> None:
    pasta_imagens = pasta_saida / "imagens"
    pasta_imagens.mkdir(parents=True, exist_ok=True)

    respostas = []
    for resposta in resultado["respostas"]:
        resposta = dict(resposta)
        vetor = resposta.pop("f", None)
        if vetor is not None and resposta["status_code"] == 200:
            nome = f"{resposta['client_id']}_{resposta['signal_id']}.png"
            salvar_imagem({**resposta, "f": vetor}, pasta_imagens / nome)
            resposta["imagem"] = f"imagens/{nome}"
        respostas.append(resposta)

    relatorio = {
        "resumo": resultado["resumo"],
        "respostas": respostas,
    }
    with (pasta_saida / "relatorio.json").open("w", encoding="utf-8") as arquivo:
        json.dump(relatorio, arquivo, indent=2, ensure_ascii=False)
    salvar_markdown(respostas, pasta_saida / "relatorio.md")


def main() -> None:
    args = ler_argumentos()
    args.saida.mkdir(parents=True, exist_ok=True)
    caminho_sequencia = args.saida / "sequencia.jsonl"
    itens = preparar_sequencia(args, caminho_sequencia)

    resultado = executar_carga(
        url_base=args.url,
        itens_sequencia=itens,
        pasta_dados=args.pasta_dados,
        max_tentativas=args.max_tentativas,
        backoff_inicial=args.backoff_inicial,
        threads_clientes=args.threads_clientes,
        salvar_f=True,
        caminho_respostas=args.saida / "respostas.jsonl",
    )
    gerar_relatorio(resultado, args.saida)
    print(json.dumps(resultado["resumo"], indent=2, ensure_ascii=False))
    print(f"Relatorio salvo em: {args.saida / 'relatorio.json'}")


if __name__ == "__main__":
    main()
