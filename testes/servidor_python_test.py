import queue
import unittest

import numpy as np

from servers.python.algoritmos import cgne, cgnr
from servers.python.fila import FilaJobs, Job, Pedido
from servers.python.modelos import Modelo
from servers.python.protocolo import interpretar_pedido


class ServidorPythonTest(unittest.TestCase):
    def setUp(self) -> None:
        self.matriz = np.eye(4, dtype=np.float32)
        self.modelos = {
            "30x30": Modelo("30x30", 2, 2, 2, self.matriz),
        }

    def test_algoritmos_resolvem_sistema_identidade(self) -> None:
        g = np.array([1, -2, 3, 4], dtype=np.float32)
        for algoritmo in (cgne, cgnr):
            f, iteracoes, erro = algoritmo(self.matriz, g)
            np.testing.assert_allclose(f, g, rtol=1e-6, atol=1e-6)
            self.assertLessEqual(iteracoes, 2)
            self.assertLess(np.linalg.norm(f - g), 1e-5)
            self.assertGreaterEqual(erro, 0.0)

    def test_pedido_valido_e_rejeicoes_de_validacao(self) -> None:
        pedido = interpretar_pedido(
            b'{"client_id":"c1","signal_id":"s1","model":"30x30",'
            b'"algorithm":"CGNR","g":[1,2,3,4]}',
            self.modelos,
        )
        self.assertEqual(pedido.client_id, "c1")
        self.assertEqual(pedido.g.dtype, np.float32)
        with self.assertRaisesRegex(ValueError, "tamanho de g"):
            interpretar_pedido(
                b'{"client_id":"c1","signal_id":"s1","model":"30x30",'
                b'"algorithm":"CGNE","g":[1,2]}',
                self.modelos,
            )
        with self.assertRaisesRegex(ValueError, "algoritmo desconhecido"):
            interpretar_pedido(
                b'{"client_id":"c1","signal_id":"s1","model":"30x30",'
                b'"algorithm":"OUTRO","g":[1,2,3,4]}',
                self.modelos,
            )

    def test_fila_limitada_e_fechamento(self) -> None:
        fila = FilaJobs(1)
        pedido = Pedido("c", "s", "30x30", "CGNE", np.zeros(4, dtype=np.float32), 0.0, "")
        job = Job(pedido, queue.Queue(maxsize=1))
        self.assertTrue(fila.inserir(job))
        outro = Pedido("c", "s2", "30x30", "CGNE", np.zeros(4, dtype=np.float32), 0.0, "")
        self.assertFalse(fila.inserir(Job(outro, queue.Queue(maxsize=1))))
        self.assertIs(fila.retirar(), job)
        fila.fechar()
        self.assertIsNone(fila.retirar())


if __name__ == "__main__":
    unittest.main()
