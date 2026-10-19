# Planejamento do projeto – CSM30 Desenvolvimento Integrado de Sistemas

Dupla: Estudante A e Estudante B

O projeto é um sistema cliente-servidor de reconstrução de imagens de ultrassom. Os clientes enviam sinais, o servidor reconstrói a imagem com CGNE ou CGNR, e a dupla compara duas versões do servidor: uma em linguagem interpretada e outra em linguagem compilada.

## 1. O que a disciplina cobra

**Avaliação.** A nota de cada atividade (N1 e N2) é 40% cliente (R), 40% servidor (P) e 20% relatório comparativo e apresentação (I). A média final é (N1 + N2) / 2 × 0,9 + participação × 0,1. Funcionalidade incompleta ou com erro de execução não conta, então é melhor entregar menos coisas funcionando do que muitas pela metade.

**Entregas no Moodle.** Revisão sobre arquiteturas, Avaliação do cliente, Avaliação do servidor, Avaliação do relatório comparativo e Entrega final.

**Encontros síncronos.** Sextas-feiras, das 16h às 17h (Google Meet). E-mail do professor: pbueno@utfpr.edu.br.

## 2. Requisitos

### Cliente

- [ ] C1: iniciar simultaneamente no mínimo 3 clientes.
- [ ] C2: cada cliente envia no mínimo 15 sinais (g), em intervalos de tempo aleatórios.
- [ ] C3: o ganho de sinal e o modelo da imagem (60×60 ou 30×30) são definidos aleatoriamente.
- [ ] C4: o ganho de sinal é calculado no cliente.
- [ ] C5: gerar um relatório com todas as imagens reconstruídas e as informações de cada uma.
- [ ] C6: a sequência de sinais enviada deve ser a mesma para as duas versões do servidor (seed fixa ou sequência gravada em arquivo).

### Servidor

- [ ] S1: uma versão em linguagem interpretada e não fortemente tipada.
- [ ] S2: uma versão em linguagem compilada e fortemente tipada.
- [ ] S3: executar o algoritmo de reconstrução (CGNE e/ou CGNR, conforme escolha do usuário).
- [ ] S4: parar quando o erro ε for menor que 1e-4 ou ao chegar a 10 iterações (o "1e10-4" do enunciado deve ser erro de digitação).
- [ ] S5: cada imagem guarda identificação do cliente, do sinal e do algoritmo, data e hora de início e de término da reconstrução e número de iterações.
- [ ] S6: objetivo principal: reconstruir o maior número de imagens no menor tempo possível.

### Relatório comparativo (versão A vs. versão B)

- [ ] R1: número total de imagens reconstruídas.
- [ ] R2: tempo total de execução.
- [ ] R3: gráfico de consumo de CPU durante a execução.
- [ ] R4: gráfico de consumo de memória durante a execução.
- [ ] R5: número médio de imagens na fila de reconstrução.
- [ ] R6: número moda de imagens na fila de reconstrução.
- [ ] R7: tempo médio de reconstrução.

### Fórmulas do enunciado

- Ganho de sinal: para cada coluna c = 1..N e cada linha l = 1..S, γ_l = 100 + (1/20) · l · √l e g[l,c] = g[l,c] · γ_l.
- Erro: ε = ‖r(i+1)‖₂ − ‖r(i)‖₂, usando o valor absoluto.
- Modelo 1: H de 50816 × 3600 (imagem 60×60, S = 794, N = 64).
- Modelo 2: H de 27904 × 900 (imagem 30×30, S = 436, N = 64).

## 3. Plano de tasks

### Fase 0: Alinhamento (semana 1, juntos)

- [ ] Ler os slides 01 a 04, o artigo Green Software e o capítulo do CGNR no Saad.
- [ ] Combinar repositório Git, estrutura de pastas e divisão de tarefas.
- [ ] Baixar o Dados.zip e descobrir o formato dos arquivos (ordem dos índices e como transformar o vetor f em imagem 60×60).
- [ ] Entregar a Revisão sobre arquiteturas, com base nos links da Wikipédia sobre arquitetura de software e modularidade e no slide de cliente-servidor.

### Fase 1: Seleção de linguagens e bibliotecas BLAS (atividade semanal 1)

- [ ] Estudante A: escolher a linguagem interpretada. Sugestão: Python com NumPy (OpenBLAS ou MKL). Python é tecnicamente fortemente tipado, só que dinâmico. Para evitar discussão, confirmar com o professor ou usar JavaScript ou MATLAB.
- [ ] Estudante B: escolher a linguagem compilada e fortemente tipada. Opções: C++ (Eigen ou OpenBLAS), Go (gonum, ótimo para concorrência) ou Rust (ndarray).
- [ ] Verificar se cada escolha tem BLAS, servidor de rede, threads ou concorrência e medição de CPU e memória.
- [ ] Escrever uma página justificando as escolhas. O artigo "Energy Efficiency across Programming Languages" pode ser reaproveitado no relatório final.

### Fase 2: Operações básicas (atividade semanal 2)

- [ ] Ler as matrizes e vetores do Dados.zip nas duas linguagens.
- [ ] Implementar MN = M·N, aM = a·M e Ma = M·a, respeitando as regras de álgebra linear (dimensões e ordem).
- [ ] Validar os resultados entre as duas linguagens (diferença numérica próxima de zero) e cronometrar.
- [ ] Atenção à memória: H do modelo 1 ocupa cerca de 1,46 GB em float64 e cerca de 730 MB em float32. Definir a precisão agora.

### Fase 3: Algoritmos de reconstrução (atividade semanal 3)

- [ ] Estudante A: implementar CGNR e CGNE na versão interpretada.
- [ ] Estudante B: implementar CGNR e CGNE na versão compilada.
- [ ] Critério de parada: ε < 1e-4 ou 10 iterações.
- [ ] Validar a imagem reconstruída com os sinais de teste do modelo 1 e do modelo 2 (devem aparecer os pontos refletores dos slides).
- [ ] Medir tempo total, memória e ocupação de CPU de uma reconstrução.
- [ ] Comparar as duas implementações (mesma imagem, mesmo número de iterações).

### Fase 4: Cliente

- [ ] Definir o protocolo (sugestão: HTTP/REST com JSON ou formato binário, ou sockets TCP). A mensagem leva id do cliente, id do sinal, modelo, algoritmo e o vetor g já com o ganho aplicado.
- [ ] Implementar o ganho de sinal no cliente.
- [ ] Criar o gerador de sequência aleatória reproduzível (modelo, ganho, intervalos e algoritmo), gravada em arquivo.
- [ ] Rodar 3 ou mais clientes em paralelo, com 15 ou mais sinais cada.
- [ ] Gerar o relatório de imagens com os metadados (S5).
- [ ] Testar o cliente contra as duas versões do servidor, sem alterar nada nele.

### Fase 5: Servidor completo

- [ ] Carregar H uma única vez, compartilhada entre as requisições.
- [ ] Implementar fila de requisições e pool de workers.
- [ ] Evitar sobreposição de threads: um BLAS multi-thread dentro de vários workers causa oversubscription. Testar `OPENBLAS_NUM_THREADS=1` com N workers.
- [ ] Registrar nos metadados início, fim, iterações, algoritmo, cliente e sinal.
- [ ] Implementar o coletor de métricas em intervalo fixo: CPU, memória e tamanho da fila.
- [ ] Calcular média e moda da fila, tempo médio de reconstrução e total de imagens.
- [ ] Repetir na outra linguagem, com a mesma interface.

### Fase 6: Saturação e controle (atividade semanal 4)

- [ ] Aumentar o número de clientes e a frequência de envio até saturar (CPU em 100%, fila crescendo, memória estourando).
- [ ] Documentar o ponto de saturação das duas versões.
- [ ] Projetar uma rotina de controle. Opções: limitar workers ao número de cores, limite de fila com rejeição ou espera, escolher algoritmo ou modelo conforme a carga, priorizar modelos menores.
- [ ] Reexecutar os testes com o controle ligado e mostrar o ganho (R1 a R7 antes e depois).

### Fase 7: Relatório comparativo e apresentação

- [ ] Rodar o experimento final com a mesma sequência de sinais nas duas versões.
- [ ] Montar R1 a R7 com tabelas e gráficos de CPU e memória.
- [ ] Escrever a discussão: desempenho, consumo de recursos, produtividade de desenvolvimento e, se couber, eficiência energética (artigo Green Software).
- [ ] Escrever a conclusão sobre a arquitetura cliente-servidor adotada.
- [ ] Preparar a apresentação, com demo ao vivo e plano B gravado.

### Fase 8: Entrega

- [ ] Testar tudo do zero em uma máquina limpa (README com instruções de execução).
- [ ] Subir os arquivos nos slots do Moodle (cliente, servidor, relatório e entrega final).
- [ ] Ensaiar a demo, já que funcionalidade com erro de execução vale zero.

## 4. Divisão sugerida

| Estudante A | Estudante B |
|---|---|
| Cliente e gerador de sequência | Servidor na versão compilada |
| Servidor na versão interpretada | Coletor de métricas e gráficos |
| Revisão sobre arquiteturas | Testes de saturação e controle |
| Texto do relatório | Texto do relatório e apresentação |

As fases 0, 1, 2, 3 e 7 são feitas juntos, e cada um revisa o código do outro.

## 5. Dúvidas para tirar com o professor

- O "1e10-4" do enunciado é na verdade 1e-4?
- O fator de redução c = ‖HᵀH‖₂ e o coeficiente de regularização λ = max(|Hᵀg|) · 0,10 são obrigatórios nos algoritmos ou só informativos?
- Python vale como linguagem "interpretada e não fortemente tipada"?
- Quais são as datas de cada entrega? Os prazos não aparecem no material, e o plano de ensino anexado é de 2017.

## 6. Observação

O formato exato dos dados (Dados.zip, sinais e matrizes H) não pôde ser conferido, pois só os PDFs foram lidos. Confirmar na Fase 0.
