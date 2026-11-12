import queue
import sys
import unittest
from pathlib import Path

import numpy as np

RAIZ = Path(__file__).resolve().parents[1]
if str(RAIZ) not in sys.path:
    sys.path.insert(0, str(RAIZ))

from servers.python.algoritmos import cgne, cgnr
from servers.python.fila import FilaJobs, Job, Pedido
from servers.python.modelos import Modelo
from servers.python.protocolo import interpretar_pedido


def criar_modelos_de_teste() -> tuple[np.ndarray, dict[str, Modelo]]:
    matriz = np.eye(4, dtype=np.float32)
    modelos = {"30x30": Modelo("30x30", 2, 2, 2, matriz)}
    return matriz, modelos


def esperar_erro(mensagem: str, funcao) -> None:
    try:
        funcao()
    except ValueError as erro:
        if mensagem not in str(erro):
            raise AssertionError(f"Erro diferente do esperado: {erro}") from erro
    else:
        raise AssertionError(f"Era esperado um erro contendo: {mensagem}")


def testar_algoritmos() -> None:
    matriz, _ = criar_modelos_de_teste()
    g = np.array([1, -2, 3, 4], dtype=np.float32)

    for algoritmo in (cgne, cgnr):
        f, iteracoes, erro = algoritmo(matriz, g)
        if not np.allclose(f, g, rtol=1e-6, atol=1e-6):
            raise AssertionError("o algoritmo nao resolveu o sistema identidade")
        if iteracoes > 2:
            raise AssertionError("o algoritmo executou mais de 2 iteracoes")
        if np.linalg.norm(f - g) >= 1e-5:
            raise AssertionError("o resultado ficou diferente do esperado")
        if erro < 0.0:
            raise AssertionError("o erro nao pode ser negativo")


def testar_validacao_do_pedido() -> None:
    _, modelos = criar_modelos_de_teste()
    pedido = interpretar_pedido(
        b'{"client_id":"c1","signal_id":"s1","model":"30x30",'
        b'"algorithm":"CGNR","g":[1,2,3,4]}',
        modelos,
    )
    if pedido.client_id != "c1":
        raise AssertionError("client_id incorreto")
    if pedido.g.dtype != np.float32:
        raise AssertionError("o vetor g deveria usar float32")

    esperar_erro(
        "tamanho de g",
        lambda: interpretar_pedido(
            b'{"client_id":"c1","signal_id":"s1","model":"30x30",'
            b'"algorithm":"CGNE","g":[1,2]}',
            modelos,
        ),
    )
    esperar_erro(
        "algoritmo desconhecido",
        lambda: interpretar_pedido(
            b'{"client_id":"c1","signal_id":"s1","model":"30x30",'
            b'"algorithm":"OUTRO","g":[1,2,3,4]}',
            modelos,
        ),
    )


def testar_fila() -> None:
    fila = FilaJobs(1)
    pedido = Pedido(
        "c", "s", "30x30", "CGNE",
        np.zeros(4, dtype=np.float32), 0.0, "",
    )
    job = Job(pedido, queue.Queue(maxsize=1))
    if not fila.inserir(job):
        raise AssertionError("a fila deveria aceitar o primeiro job")

    outro = Pedido(
        "c", "s2", "30x30", "CGNE",
        np.zeros(4, dtype=np.float32), 0.0, "",
    )
    if fila.inserir(Job(outro, queue.Queue(maxsize=1))):
        raise AssertionError("a fila deveria rejeitar o segundo job")
    if fila.retirar() is not job:
        raise AssertionError("a fila deveria devolver o primeiro job")
    fila.fechar()
    if fila.retirar() is not None:
        raise AssertionError("a fila fechada deveria retornar None")


def main() -> None:
    testes = [testar_algoritmos, testar_validacao_do_pedido, testar_fila]
    for teste in testes:
        teste()
        print(f"OK: {teste.__name__}")
    print(f"{len(testes)} testes passaram.")


def load_tests(_loader, _tests, _pattern):
    suite = unittest.TestSuite()
    for teste in (testar_algoritmos, testar_validacao_do_pedido, testar_fila):
        suite.addTest(unittest.FunctionTestCase(teste))
    return suite


if __name__ == "__main__":
    main()
