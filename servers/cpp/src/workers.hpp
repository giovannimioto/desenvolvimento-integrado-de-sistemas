#ifndef WORKERS_HPP
#define WORKERS_HPP

#include "algoritmos.hpp"
#include "estatisticas.hpp"
#include "fila_jobs.hpp"
#include "log_csv.hpp"
#include "modelos.hpp"

Resposta montar_resposta(const Pedido& pedido,
                         Relogio::time_point inicio,
                         Relogio::time_point fim,
                         Relogio::time_point recebido_em,
                         ResultadoReconstrucao& resultado);

void laco_worker(FilaJobs& fila,
                 const MapaModelos& modelos,
                 LogCsv& log,
                 Estatisticas& est);

#endif

