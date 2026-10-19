import time
from pathlib import Path

import numpy as np
import pandas as pd

RAIZ = Path(__file__).resolve().parents[2]
caminho = RAIZ / "data" / "H-1.csv"

t = time.time()
H = pd.read_csv(caminho, header=None).to_numpy(dtype=np.float32)
print("formato:", H.shape, "| tempo de leitura:", round(time.time() - t, 1), "s")

np.save(caminho.with_suffix(".npy"), H)
print("salvo em:", caminho.with_suffix(".npy"))