#ifndef SERVIDOR_HTTP_HPP
#define SERVIDOR_HTTP_HPP

#include "config.hpp"
#include "estatisticas.hpp"
#include "fila_jobs.hpp"
#include "modelos.hpp"

#include <string>

// Valida o JSON de POST /reconstruir (modelo, algoritmo e tamanho de g).
bool interpretar_pedido(const std::string& corpo_json,
                        const MapaModelos& modelos,
                        Pedido& saida,
                        std::string& erro);

// Executa o servidor HTTP nas rotas /reconstruir e /status ate receber parada.
void executar_servidor_http(const Config& cfg,
                            const MapaModelos& modelos,
                            FilaJobs& fila,
                            Estatisticas& est);

// Solicita o encerramento do servidor HTTP ativo (chamado por SIGINT/SIGTERM).
void solicitar_parada_servidor_http();

#endif

