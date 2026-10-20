import time
import numpy as np
import matplotlib.pyplot as plt

H = np.load("data/H-2.npy")
g = np.load("data/g-30x30-1.npy").ravel()

f = np.zeros(H.shape[1], dtype=np.float32)


r = g - H @ f
z = H.T @ r
p = z.copy()

inicio = time.perf_counter()
iteracoes = 0

for i in range(10):
    w = H @ p
    alpha = (z @ z) / (w @ w)

    f = f + alpha * p
    r_novo = r - alpha * w
    z_novo = H.T @ r_novo
    beta = (z_novo @ z_novo) / (z @ z)
    p = z_novo + beta * p

    erro = abs(np.linalg.norm(r_novo) - np.linalg.norm(r))
    r, z = r_novo, z_novo
    iteracoes = i + 1
    print(f"iteração {iteracoes}: erro = {erro:.6f}")

    if erro < 1e-4:
        break

print("iterações:", iteracoes, "| tempo:", round(time.perf_counter() - inicio, 3), "s")

imagem = f.reshape(30, 30, order="F")
plt.imshow(imagem, cmap="gray")
plt.title("Imagem reconstruída (CGNR)")
plt.show()