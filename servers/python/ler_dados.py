from pathlib import Path

import numpy as np
import pandas as pd

RAIZ = Path(__file__).resolve().parents[2]
DATA = RAIZ / "data"

for csv in sorted(DATA.glob("*.csv")):
    npy = csv.with_suffix(".npy")
    binf = csv.with_suffix(".bin")
    if npy.exists() and binf.exists():
        print("já convertido:", csv.name)
        continue
    a = pd.read_csv(csv, header=None).to_numpy(dtype=np.float32)
    np.save(npy, a)
    a.tofile(binf)
    print(csv.name, "->", a.shape)