"""Compara a reconstrucao C++ (reconstruir_offline) contra as referencias NumPy e gera PNGs."""

import json
import subprocess
import sys
import tempfile
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.image as mpimg
import matplotlib.pyplot as plt
import numpy as np

RAIZ = Path(__file__).resolve().parents[2]
if str(RAIZ) not in sys.path:
    sys.path.insert(0, str(RAIZ))

from carga.ganho import DIMENSOES_MODELO

DATA = RAIZ / "data"
PASTA_REF = DATA / "referencias"
BIN_OFFLINE = RAIZ / "servers" / "cpp" / "build" / "reconstruir_offline"

IMAGENS_SLIDES = {
    "g-30x30-1": "f-30x30-1.png",
    "g-30x30-2": "f-30x30-2.png",
    "G-1": "F-1.png",
    "G-2": "F-2.png",
}


def extrair_campos_stdout(texto: str) -> dict[str, str]:
    campos = {}
    for token in texto.strip().split():
        if "=" in token:
            k, v = token.split("=", 1)
            campos[k] = v
    return campos


def salvar_comparacao_png(
    sinal: str,
    algoritmo: str,
    lado: int,
    f_py: np.ndarray,
    f_cpp: np.ndarray,
    iter_py: int,
    iter_cpp: int,
    erro_rel: float,
    destino: Path,
) -> None:
    img_py = np.abs(f_py.reshape(lado, lado, order="F"))
    img_cpp = np.abs(f_cpp.reshape(lado, lado, order="F"))

    arq_slide = DATA / IMAGENS_SLIDES[sinal] if sinal in IMAGENS_SLIDES else None
    tem_slide = arq_slide is not None and arq_slide.exists()
    n_cols = 3 if tem_slide else 2

    fig, eixos = plt.subplots(1, n_cols, figsize=(4.2 * n_cols, 4.0))
    eixos[0].imshow(img_py, cmap="gray")
    eixos[0].set_title(f"Python NumPy ({algoritmo})\niter={iter_py}")
    eixos[0].axis("off")

    eixos[1].imshow(img_cpp, cmap="gray")
    eixos[1].set_title(f"C++ Eigen ({algoritmo})\niter={iter_cpp} | rel={erro_rel:.2e}")
    eixos[1].axis("off")

    if tem_slide:
        img_ref = mpimg.imread(arq_slide)
        eixos[2].imshow(img_ref, cmap="gray")
        eixos[2].set_title(f"Referencia Enunciado\n({arq_slide.name})")
        eixos[2].axis("off")

    fig.suptitle(f"Sinal: {sinal} ({lado}x{lado}) — {algoritmo}", fontsize=11)
    fig.tight_layout()
    fig.savefig(destino, dpi=120)
    plt.close(fig)


def main() -> None:
    caminho_meta = PASTA_REF / "metadados_referencias.json"
    if not caminho_meta.exists():
        raise FileNotFoundError(
            f"{caminho_meta} nao encontrado. Execute gerar_referencias.py primeiro."
        )
    if not BIN_OFFLINE.exists():
        raise FileNotFoundError(
            f"{BIN_OFFLINE} nao encontrado. Compile com 'make -C servers/cpp'."
        )

    with open(caminho_meta, "r", encoding="utf-8") as arq:
        metadados = json.load(arq)

    falhas = []
    relatorio_comparacao = {}

    print(
        f"{'Caso':20s} | {'Iter Py':>7s} | {'Iter C++':>8s} | "
        f"{'Erro Rel':>10s} | {'Py (ms)':>8s} | {'C++ (ms)':>8s} | Status"
    )
    print("-" * 82)

    with tempfile.TemporaryDirectory() as tmpdir:
        for chave, info in metadados.items():
            modelo = info["modelo"]
            sinal = info["sinal"]
            algoritmo = info["algoritmo"]
            iter_py = int(info["iteracoes"])
            tempo_py_ms = float(info["tempo_py_ms"])
            _, _, lado, _ = DIMENSOES_MODELO[modelo]

            f_py = np.load(PASTA_REF / f"{chave}.npy").ravel()
            saida_csv = Path(tmpdir) / f"{chave}.csv"

            cmd = [
                str(BIN_OFFLINE),
                "--modelo", modelo,
                "--algoritmo", algoritmo,
                "--sinal", str(DATA / f"{sinal}.bin"),
                "--pasta-dados", str(DATA),
                "--ganho",
                "--saida", str(saida_csv),
            ]
            proc = subprocess.run(cmd, capture_output=True, text=True, check=True)
            campos = extrair_campos_stdout(proc.stdout)
            iter_cpp = int(campos["iteracoes"])
            tempo_cpp_ms = float(campos["tempo_ms"])

            f_cpp = np.loadtxt(saida_csv, dtype=np.float32).ravel()
            norma_py = float(np.linalg.norm(f_py))
            erro_rel = float(np.linalg.norm(f_cpp - f_py) / (norma_py if norma_py > 0 else 1.0))

            diff_iter = abs(iter_cpp - iter_py)
            aprovado = (erro_rel < 1e-3) and (diff_iter <= 1)
            status = "PASS" if aprovado else "FAIL"
            if not aprovado:
                falhas.append(f"{chave}: erro_rel={erro_rel:.3e}, diff_iter={diff_iter}")

            png_saida = PASTA_REF / f"validacao_{chave}.png"
            salvar_comparacao_png(
                sinal, algoritmo, lado, f_py, f_cpp, iter_py, iter_cpp, erro_rel, png_saida
            )

            relatorio_comparacao[chave] = {
                "modelo": modelo,
                "sinal": sinal,
                "algoritmo": algoritmo,
                "iter_py": iter_py,
                "iter_cpp": iter_cpp,
                "erro_relativo": erro_rel,
                "tempo_py_ms": tempo_py_ms,
                "tempo_cpp_ms": tempo_cpp_ms,
                "speedup": round(tempo_py_ms / tempo_cpp_ms, 2) if tempo_cpp_ms > 0 else None,
                "png": str(png_saida.relative_to(RAIZ)),
                "aprovado": aprovado,
            }

            print(
                f"{chave:20s} | {iter_py:7d} | {iter_cpp:8d} | "
                f"{erro_rel:10.3e} | {tempo_py_ms:8.2f} | {tempo_cpp_ms:8.2f} | {status}"
            )

    with open(PASTA_REF / "comparacao_cpp_python.json", "w", encoding="utf-8") as arq:
        json.dump(relatorio_comparacao, arq, indent=2, ensure_ascii=False)

    if falhas:
        print("\nFALHAS encontradas:")
        for f in falhas:
            print(" -", f)
        sys.exit(1)

    print(f"\nTodos os {len(metadados)} casos aprovados (erro_rel < 1e-3, iteracoes +-1).")
    print(f"PNGs de conferencia visual salvos em {PASTA_REF.relative_to(RAIZ)}/validacao_*.png")


if __name__ == "__main__":
    main()

