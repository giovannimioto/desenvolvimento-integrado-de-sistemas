import time
import numpy as np
import matplotlib.pyplot as plt

H = np.load("data/H-2.npy")
g = np.load("data/g-30x30-1.npy").ravel()

f = np.zeros(H.shape[1], dtype=np.float32)

r = g - H @ f
p = H.T @ r

inicio = time.perf_counter()
iteracoes = 0

for i in range(10):
    alpha = (r @ r) / (p @ p)

    f = f + alpha * p
    r_novo = r - alpha * (H @ p)
    beta = (r_novo @ r_novo) / (r @ r)
    p = H.T @ r_novo + beta * p

    erro = abs(np.linalg.norm(r_novo) - np.linalg.norm(r))
    r = r_novo
    iteracoes = i + 1
    print(f"iteração {iteracoes}: erro = {erro:.6f}")

    if erro < 1e-4:
        break

print("iterações:", iteracoes, "| tempo:", round(time.perf_counter() - inicio, 3), "s")
print("resíduo relativo:", np.linalg.norm(g - H @ f) / np.linalg.norm(g))

imagem = np.abs(f.reshape(30, 30, order="F"))
plt.imshow(imagem, cmap="gray")
plt.title("Imagem reconstruída (CGNE)")
plt.show()