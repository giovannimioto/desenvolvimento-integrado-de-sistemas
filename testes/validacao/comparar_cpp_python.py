"""Compara reconstruções C++ com referências NumPy e gera imagens."""

import json
import sys
import tempfile
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import numpy as np

RAIZ = Path(__file__).resolve().parents[2]
if str(RAIZ) not in sys.path:
    sys.path.insert(0, str(RAIZ))

from utilitarios import DIMENSOES_MODELO, executar_cpp, salvar_comparacao_png

DATA = RAIZ / "data"
PASTA_REF = DATA / "referencias"
BIN_OFFLINE = RAIZ / "servers" / "cpp" / "build" / "reconstruir_offline"
IMAGENS_SLIDES = {
    "g-30x30-1": "f-30x30-1.png", "g-30x30-2": "f-30x30-2.png",
    "G-1": "F-1.png", "G-2": "F-2.png",
}


def carregar_entradas() -> dict:
    meta = PASTA_REF / "metadados_referencias.json"
    if not meta.exists():
        raise FileNotFoundError(f"{meta} nao encontrado. Execute gerar_referencias.py primeiro.")
    if not BIN_OFFLINE.exists():
        raise FileNotFoundError(f"{BIN_OFFLINE} nao encontrado. Compile com 'make -C servers/cpp'.")
    with open(meta, encoding="utf-8") as arquivo:
        return json.load(arquivo)


def comparar_caso(chave: str, info: dict, temporario: Path) -> tuple[dict, str | None]:
    modelo, sinal, algoritmo = info["modelo"], info["sinal"], info["algoritmo"]
    _, _, lado, _ = DIMENSOES_MODELO[modelo]
    f_py = np.load(PASTA_REF / f"{chave}.npy").ravel()
    f_cpp, campos = executar_cpp(
        BIN_OFFLINE, modelo, algoritmo, DATA / f"{sinal}.bin", DATA,
        temporario / f"{chave}.csv",
    )
    iter_py, iter_cpp = int(info["iteracoes"]), int(campos["iteracoes"])
    tempo_py, tempo_cpp = float(info["tempo_py_ms"]), float(campos["tempo_ms"])
    norma = float(np.linalg.norm(f_py))
    erro_rel = float(np.linalg.norm(f_cpp - f_py) / (norma if norma > 0 else 1.0))
    aprovado = erro_rel < 1e-3 and abs(iter_cpp - iter_py) <= 1
    png = PASTA_REF / f"validacao_{chave}.png"
    salvar_comparacao_png(
        sinal, algoritmo, lado, f_py, f_cpp, iter_py, iter_cpp, erro_rel, png,
        DATA / IMAGENS_SLIDES[sinal] if sinal in IMAGENS_SLIDES else None,
    )
    relatorio = {
        "modelo": modelo, "sinal": sinal, "algoritmo": algoritmo,
        "iter_py": iter_py, "iter_cpp": iter_cpp, "erro_relativo": erro_rel,
        "tempo_py_ms": tempo_py, "tempo_cpp_ms": tempo_cpp,
        "speedup": round(tempo_py / tempo_cpp, 2) if tempo_cpp > 0 else None,
        "png": str(png.relative_to(RAIZ)), "aprovado": aprovado,
    }
    falha = None if aprovado else f"{chave}: erro_rel={erro_rel:.3e}, diff_iter={abs(iter_cpp - iter_py)}"
    return relatorio, falha


def main() -> None:
    metadados = carregar_entradas()
    relatorio, falhas = {}, []
    print(f"{'Caso':20s} | {'Iter Py':>7s} | {'Iter C++':>8s} | {'Erro Rel':>10s} | {'Py (ms)':>8s} | {'C++ (ms)':>8s} | Status")
    print("-" * 82)
    with tempfile.TemporaryDirectory() as pasta:
        for chave, info in metadados.items():
            resultado, falha = comparar_caso(chave, info, Path(pasta))
            relatorio[chave] = resultado
            falhas.append(falha) if falha else None
            status = "PASS" if resultado["aprovado"] else "FAIL"
            print(f"{chave:20s} | {resultado['iter_py']:7d} | {resultado['iter_cpp']:8d} | "
                  f"{resultado['erro_relativo']:10.3e} | {resultado['tempo_py_ms']:8.2f} | "
                  f"{resultado['tempo_cpp_ms']:8.2f} | {status}")
    with open(PASTA_REF / "comparacao_cpp_python.json", "w", encoding="utf-8") as arquivo:
        json.dump(relatorio, arquivo, indent=2, ensure_ascii=False)
    if falhas:
        print("\nFALHAS encontradas:\n - " + "\n - ".join(falhas))
        sys.exit(1)
    print(f"\nTodos os {len(metadados)} casos aprovados (erro_rel < 1e-3, iteracoes +-1).")
    print(f"PNGs de conferencia visual salvos em {PASTA_REF.relative_to(RAIZ)}/validacao_*.png")


if __name__ == "__main__":
    main()
