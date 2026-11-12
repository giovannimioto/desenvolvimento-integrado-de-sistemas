"""Prepara os dados em data/: extrai ZIPs e gera os arquivos .bin/.npy."""

import subprocess
import sys
import zipfile
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[2]
DATA = RAIZ / "data"
LER_DADOS = Path(__file__).with_name("ler_dados.py")

TAMANHOS_ESPERADOS = {
    "H-1.bin": 50816 * 3600 * 4,
    "H-2.bin": 27904 * 900 * 4,
    "g-30x30-1.bin": 27904 * 4,
    "g-30x30-2.bin": 27904 * 4,
    "A-30x30-1.bin": 27904 * 4,
    "G-1.bin": 50816 * 4,
    "G-2.bin": 50816 * 4,
    "A-60x60-1.bin": 50816 * 4,
}


def extrair_sem_macosx(caminho_zip: Path, destino: Path) -> list[Path]:
    destino.mkdir(parents=True, exist_ok=True)
    extraidos = []
    with zipfile.ZipFile(caminho_zip, "r") as zf:
        for membro in zf.namelist():
            if membro.startswith("__MACOSX") or Path(membro).name.startswith("._"):
                continue
            alvo = destino / Path(membro).name
            with zf.open(membro) as origem, open(alvo, "wb") as saida:
                while bloco := origem.read(1024 * 1024):
                    saida.write(bloco)
            extraidos.append(alvo)
            print(f"Extraido: {alvo.relative_to(RAIZ)}")
    return extraidos


def main() -> None:
    dados_zip = DATA / "Dados.zip"
    if not dados_zip.exists():
        raise FileNotFoundError(f"Arquivo nao encontrado: {dados_zip}")
    extrair_sem_macosx(dados_zip, DATA / "fase2")

    csvs_temporarios = []
    for nome_base in ("H-1", "H-2"):
        bin_path = DATA / f"{nome_base}.bin"
        npy_path = DATA / f"{nome_base}.npy"
        csv_path = DATA / f"{nome_base}.csv"
        zip_path = DATA / f"{nome_base}.csv.zip"
        if bin_path.exists() and npy_path.exists():
            print(f"{nome_base}.bin e {nome_base}.npy ja existem; pulando extracao do ZIP.")
            continue
        if not csv_path.exists():
            if not zip_path.exists():
                raise FileNotFoundError(f"Arquivo nao encontrado: {zip_path}")
            extrair_sem_macosx(zip_path, DATA)
            csvs_temporarios.append(csv_path)

    subprocess.run([sys.executable, str(LER_DADOS)], check=True)

    for nome_bin, bytes_esperados in TAMANHOS_ESPERADOS.items():
        caminho = DATA / nome_bin
        if not caminho.exists():
            raise RuntimeError(f"Arquivo esperado nao foi gerado: {caminho}")
        tamanho = caminho.stat().st_size
        if tamanho != bytes_esperados:
            raise RuntimeError(
                f"Tamanho incorreto em {nome_bin}: {tamanho} bytes "
                f"(esperado {bytes_esperados})"
            )
        print(f"OK: {nome_bin} ({tamanho:,} bytes)")

    for csv_temp in csvs_temporarios:
        if csv_temp.exists():
            csv_temp.unlink()
            print(f"Removido CSV temporario ja convertido: {csv_temp.name}")


if __name__ == "__main__":
    main()
