import time
import numpy as np

H = np.load("data/H-2.npy")
g = np.load("data/g-30x30-1.npy").ravel()
f = np.random.rand(900).astype(np.float32)

t = time.perf_counter()
MN = H.T @ H
print("MN:", MN.shape, time.perf_counter() - t, "s")

t = time.perf_counter()
aM = 2.0 * H 
print("aM:", aM.shape, time.perf_counter() - t, "s")

t = time.perf_counter()
Ma = H @ f
print("Ma:", Ma.shape, time.perf_counter() - t, "s")