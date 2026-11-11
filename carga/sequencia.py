"""Gerador e leitor de sequencia reprodutivel de sinais em formato JSONL."""

import argparse
import json
import random
from pathlib import Path

SINAIS_POR_MODELO = {
    "30x30": ["g-30x30-1", "g-30x30-2", "A-30x30-1"],
    "60x60": ["G-1", "G-2", "A-60x60-1"],
}


def gerar_sequencia(
    clientes: int = 3,
    sinais_por_cliente: int = 15,
    seed: int = 42,
    intervalo_min: float = 0.5,
    intervalo_max: float = 2.0,
    modelos: list[str] | None = None,
    algoritmos: list[str] | None = None,
) -> list[dict]:
    if modelos is None:
        modelos = ["30x30", "60x60"]
    if algoritmos is None:
        algoritmos = ["CGNE", "CGNR"]

    rng = random.Random(seed)
    itens = []
    for c in range(1, clientes + 1):
        cid = f"c{c}"
        for s in range(1, sinais_por_cliente + 1):
            sid = f"{cid}-s{s:02d}"
            modelo = rng.choice(modelos)
            arq_sinal = rng.choice(SINAIS_POR_MODELO[modelo])
            algoritmo = rng.choice(algoritmos)
            atraso = round(rng.uniform(intervalo_min, intervalo_max), 3)
            itens.append({
                "client_id": cid,
                "signal_id": sid,
                "model": modelo,
                "signal_file": arq_sinal,
                "algorithm": algoritmo,
                "delay_s": atraso,
            })
    return itens


def salvar_sequencia_jsonl(itens: list[dict], caminho: Path) -> None:
    caminho.parent.mkdir(parents=True, exist_ok=True)
    with open(caminho, "w", encoding="utf-8") as arq:
        for item in itens:
            arq.write(json.dumps(item, ensure_ascii=False) + "\n")


def ler_sequencia_jsonl(caminho: Path) -> list[dict]:
    itens = []
    with open(caminho, "r", encoding="utf-8") as arq:
        for linha in arq:
            linha = linha.strip()
            if linha:
                itens.append(json.loads(linha))
    return itens


def main() -> None:
    parser = argparse.ArgumentParser(description="Gera sequencia reprodutivel de sinais em JSONL.")
    parser.add_argument("--clientes", type=int, default=3)
    parser.add_argument("--sinais", type=int, default=15)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--intervalo", type=float, nargs=2, default=[0.5, 2.0])
    parser.add_argument("--modelos", type=str, default="30x30,60x60")
    parser.add_argument("--algoritmos", type=str, default="CGNE,CGNR")
    parser.add_argument("--saida", type=Path, required=True)
    args = parser.parse_args()

    modelos = [m.strip() for m in args.modelos.split(",") if m.strip()]
    algoritmos = [a.strip() for a in args.algoritmos.split(",") if a.strip()]
    itens = gerar_sequencia(
        clientes=args.clientes,
        sinais_por_cliente=args.sinais,
        seed=args.seed,
        intervalo_min=args.intervalo[0],
        intervalo_max=args.intervalo[1],
        modelos=modelos,
        algoritmos=algoritmos,
    )
    salvar_sequencia_jsonl(itens, args.saida)
    print(f"Sequencia gerada: {len(itens)} envios em {args.saida}")


if __name__ == "__main__":
    main()

