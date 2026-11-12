# Roteiro de Apresentação

## 1. Abrir o projeto

### Windows — PowerShell

```powershell
cd C:\Users\giova\Documents\UTFPR\desenvolvimento-integrado-de-sistemas
.\dis_venv\Scripts\Activate.ps1
```

### Linux — Bash

```bash
cd ~/desenvolvimento-integrado-de-sistemas
source dis_venv/bin/activate
```

## 2. Preparar os dados

Execute apenas se os arquivos da pasta `data` ainda não existirem:

#### Windows — PowerShell

```powershell
python servers/python/preparar_dados.py
```

#### Linux — Bash

```bash
python servers/python/preparar_dados.py
```

## 3. Compilar o servidor C++

### Windows — PowerShell

```powershell
mingw32-make -C servers/cpp
```

Caso `mingw32-make` não esteja disponível:

```powershell
make -C servers/cpp
```

### Linux — Bash

```bash
make -C servers/cpp
```

## 4. Demonstrar o servidor Python

### Windows — Terminal 1 — PowerShell

```powershell
python servers/python/servidor.py --port 8081 --workers 4 --max-queue 8
```

### Windows — Terminal 2 — PowerShell

```powershell
cd C:\Users\giova\Documents\UTFPR\desenvolvimento-integrado-de-sistemas
.\dis_venv\Scripts\Activate.ps1

python testes/smoke/smoke_demo.py --perfil demo --url http://127.0.0.1:8081
```

### Linux — Terminal 1 — Bash

```bash
python servers/python/servidor.py --port 8081 --workers 4 --max-queue 8
```

### Linux — Terminal 2 — Bash

```bash
cd ~/desenvolvimento-integrado-de-sistemas
source dis_venv/bin/activate
python testes/smoke/smoke_demo.py --perfil demo --url http://127.0.0.1:8081
```

O teste demonstra:

- Comunicação HTTP;
- Reconstruções CGNE e CGNR;
- Modelos 30x30 e 60x60;
- Clientes simultâneos;
- Controle da fila;
- Respostas HTTP 503;
- Retry automático;
- Geração das imagens reconstruídas.

O cliente também pode ser executado diretamente para gerar a sequência e o
relatório das imagens:

```powershell
python client/cliente.py --url http://127.0.0.1:8081
```

Para comparar os dois servidores com exatamente os mesmos sinais, reutilize o
arquivo `resultados/cliente/sequencia.jsonl` na segunda execução:

```powershell
python client/cliente.py --url http://127.0.0.1:8080 `
  --sequencia resultados/cliente/sequencia.jsonl `
  --saida resultados/cliente-cpp
```

Para mostrar o status do servidor:

### Windows — PowerShell

```powershell
curl http://127.0.0.1:8081/status
```

### Linux — Bash

```bash
curl http://127.0.0.1:8081/status
```

## 5. Demonstrar o servidor C++

### Windows — PowerShell

```powershell
python testes/smoke/smoke_demo.py --perfil demo
```

### Linux — Bash

```bash
python testes/smoke/smoke_demo.py --perfil demo
```

O teste inicia o servidor C++ automaticamente, executa as reconstruções e encerra o processo ao final.

## 6. Comparar C++ e Python

Gerar as referências NumPy:

### Windows — PowerShell

```powershell
python testes/validacao/gerar_referencias.py
```

### Linux — Bash

```bash
python testes/validacao/gerar_referencias.py
```

Comparar os resultados:

### Windows — PowerShell

```powershell
python testes/validacao/comparar_cpp_python.py
```

### Linux — Bash

```bash
python testes/validacao/comparar_cpp_python.py
```

Essa comparação verifica:

- Resultado reconstruído;
- Erro relativo;
- Número de iterações;
- Tempo de execução;
- Imagens geradas por cada versão.

## 7. Executar os experimentos completos

Se houver tempo disponível:

### Windows — PowerShell

```powershell
python metricas/executar_experimento.py --cenario todos
```

### Linux — Bash

```bash
python metricas/executar_experimento.py --cenario todos
```

Esse comando executa:

- **E0:** varredura do número de workers;
- **E1:** cenário baseline;
- **E2:** saturação sem controle de fila;
- **E3:** saturação com controle de fila.

Os relatórios serão salvos em:

```text
resultados/
```

## 8. Gerar comparação entre experimentos

Exemplo:

### Windows — PowerShell

```powershell
python metricas/relatorio.py --comparar `
  resultados/E2_saturacao_sem_controle `
  resultados/E3_saturacao_com_controle
```

### Linux — Bash

```bash
python metricas/relatorio.py --comparar \
  resultados/E2_saturacao_sem_controle \
  resultados/E3_saturacao_com_controle
```

## Ordem recomendada para explicar ao professor

1. Apresentar a arquitetura cliente-servidor.
2. Mostrar os servidores Python e C++.
3. Executar o smoke test do Python.
4. Mostrar o endpoint `/status`.
5. Executar o smoke test do C++.
6. Executar a comparação numérica entre as versões.
7. Mostrar os relatórios e gráficos gerados.
8. Explicar que os experimentos E0–E3 medem desempenho, fila, CPU e memória.
