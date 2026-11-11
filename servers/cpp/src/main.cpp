#include "config.hpp"
#include "estatisticas.hpp"
#include "fila_jobs.hpp"
#include "log_csv.hpp"
#include "modelos.hpp"
#include "servidor_http.hpp"
#include "workers.hpp"

#include <csignal>
#include <iostream>
#include <thread>
#include <vector>

namespace {
void tratar_sinal(int) {
    solicitar_parada_servidor_http();
}
}  // namespace

int main(int argc, char** argv) {
    std::signal(SIGINT, tratar_sinal);
    std::signal(SIGTERM, tratar_sinal);

    const Config cfg = ler_config(argc, argv);
    const MapaModelos modelos = carregar_modelos(cfg);

    FilaJobs fila(static_cast<std::size_t>(cfg.max_fila > 0 ? cfg.max_fila : 0));
    LogCsv log(cfg.pasta_logs);
    Estatisticas est;

    std::cout << "[Servidor C++] Log CSV: " << log.caminho_arquivo() << "\n";

    std::vector<std::thread> pool_workers;
    pool_workers.reserve(static_cast<std::size_t>(cfg.workers));
    for (int i = 0; i < cfg.workers; ++i) {
        pool_workers.emplace_back(laco_worker,
                                  std::ref(fila),
                                  std::cref(modelos),
                                  std::ref(log),
                                  std::ref(est));
    }

    executar_servidor_http(cfg, modelos, fila, est);

    fila.fechar();
    for (auto& t : pool_workers) {
        if (t.joinable()) {
            t.join();
        }
    }
    std::cout << "[Servidor C++] Encerrado com sucesso. Total processados: "
              << est.processados.load() << std::endl;
    return 0;
}
