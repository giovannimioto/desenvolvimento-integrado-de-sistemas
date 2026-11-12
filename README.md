# Desenvolvimento Integrado de Sistemas (ICSM31)

Sistema cliente-servidor para reconstrução de imagens de ultrassom utilizando os algoritmos iterativos **CGNE** e **CGNR**, com versões de servidor em **Python (NumPy)** e **C++ (Eigen3)**.

## Estrutura do projeto

- `servers/python/`: servidor Python modular (`config.py`, `modelos.py`,
  `algoritmos.py`, `fila.py`, `protocolo.py`, `logging_csv.py` e
  `servidor_http.py`).
- `servers/cpp/`: servidor HTTP em C++17 + Eigen3, ferramentas de validação offline e testes unitários.
- `carga/`: cálculo de ganho, geração de sequência reprodutível (`.jsonl`) e cliente de carga concorrente.
- `metricas/`: coletor de CPU/RAM (`psutil`) e fila (`/status`), gerador de relatórios `R1`-`R7` e orquestrador de experimentos.
- `utilitarios.py`: biblioteca interna com leitura e gravação de arquivos, controle
  de processos, gráficos e funções usadas na validação Python vs. C++.
- `servers/python/preparar_dados.py`: extração dos arquivos compactados e geração dos binários `.bin`/`.npy` em `data/`.
- `testes/validacao/` e `testes/smoke/`: validação numérica/visual C++ vs. Python e smoke test ponta a ponta.

## Como entender o servidor Python

O fluxo principal é propositalmente direto:

1. `servidor.py` lê a configuração e carrega as matrizes uma única vez.
2. `servidor_http.py` recebe a requisição, coloca o trabalho na fila e inicia os workers.
3. `protocolo.py` valida o JSON e transforma os dados em um `Pedido`.
4. `algoritmos.py` executa CGNE ou CGNR.
5. `logging_csv.py` registra os metadados e `protocolo.py` monta a resposta JSON.

Essa separação deixa cada arquivo com uma responsabilidade simples: configuração,
dados, protocolo, fila, algoritmo ou registro. Para acompanhar uma requisição,
basta seguir essa ordem, sem precisar conhecer todos os módulos ao mesmo tempo.

## Pré-requisitos

### Linux (Ubuntu / Debian)
```bash
sudo apt update
sudo apt install -y build-essential libeigen3-dev pkg-config python3-venv
```

### Linux (Arch / CachyOS)
```bash
sudo pacman -S --needed base-devel eigen pkgconf python
```

### Windows (MSYS2 UCRT64)
```bash
pacman -S --needed mingw-w64-ucrt-x86_64-gcc mingw-w64-ucrt-x86_64-eigen3 mingw-w64-ucrt-x86_64-pkgconf make
```

As dependências C++ `httplib.h` (`v0.18.3`, licença MIT) e `json.hpp` (`v3.11.3`, licença MIT) já estão incluídas em `servers/cpp/third_party/`.

## Configuração e compilação

```bash
# Ambiente Python
python3 -m venv dis_venv
source dis_venv/bin/activate
pip install -r requirements.txt

# Extração dos dados e conversão para .bin/.npy (float32)
python servers/python/preparar_dados.py

# Compilação e testes unitários do servidor C++
make -C servers/cpp
make -C servers/cpp test
```

Caso ocorra *segfault* no MinGW-w64 (Windows) por alinhamento AVX2 na pilha, recompile com:
```bash
make -C servers/cpp clean
make -C servers/cpp ARCH_FLAGS="-mavx2 -mfma -Wa,-muse-unaligned-vector-move"
# ou sem AVX2:
make -C servers/cpp ARCH_FLAGS=
```

## Execução do servidor C++

```bash
./servers/cpp/build/servidor --port 8080 --workers 4 --max-queue 8
```

Opções disponíveis (prioridade: CLI > variável de ambiente > padrão):

| Flag | Variável de ambiente | Padrão | Descrição |
|---|---|---|---|
| `--port` / `--porta` | `SERVIDOR_PORTA` | `8080` | Porta HTTP |
| `--workers` | `SERVIDOR_WORKERS` | núcleos / 2 | Threads de reconstrução |
| `--max-queue` / `--max-fila` | `SERVIDOR_MAX_FILA` | `0` (ilimitada) | Limite da fila (`> 0` retorna HTTP `503`) |
| `--http-threads` | `SERVIDOR_THREADS_HTTP` | `128` | Pool de threads HTTP |
| `--data-dir` / `--pasta-dados` | `SERVIDOR_PASTA_DADOS` | `data` | Diretório das matrizes `.bin` |
| `--log-dir` / `--pasta-logs` | `SERVIDOR_PASTA_LOGS` | `logs/cpp` | Diretório dos logs CSV |
| `--modelos` / `--models` | `SERVIDOR_MODELOS` | `30x30,60x60` | Modelos carregados na inicialização |

## Execução do servidor Python

O servidor Python implementa o mesmo protocolo HTTP, fila de reconstrução, pool de
workers, limite de fila e log CSV do servidor C++:

```bash
python servers/python/servidor.py --port 8081 --workers 4 --max-queue 8
```

As mesmas opções de CLI e variáveis de ambiente do servidor C++ são aceitas. O
diretório de logs padrão é `logs/python`; use `--pasta-logs` para alterá-lo.

## Validação e experimentos

```bash
# Operações matriciais contra Dados.zip
./servers/cpp/build/fase2_operacoes data/fase2

# Validação numérica e visual (CGNE e CGNR) contra NumPy
python testes/validacao/gerar_referencias.py
python testes/validacao/comparar_cpp_python.py

# Smoke test ponta a ponta
python testes/smoke/smoke_demo.py --perfil demo

# Bateria de experimentos (varredura E0, baseline E1, saturação E2 e controle E3)
python metricas/executar_experimento.py --cenario todos

# Comparação entre dois experimentos (ex.: Python vs. C++)
python metricas/relatorio.py --comparar resultados/<exp_a> resultados/<exp_b>
```

## Endpoints HTTP

- `POST /reconstruir`: recebe `{client_id, signal_id, model, algorithm, g}` e retorna os metadados (`started_at`, `finished_at`, `iterations`) e o vetor reconstruído `f` (`400` para entrada inválida, `503` com `Retry-After: 1` quando `--max-queue` estiver cheio).
- `GET /status`: retorna `{queue_size, workers, processed, in_progress, rejected, max_queue}`.
