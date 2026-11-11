#include "config.hpp"

#include <algorithm>
#include <cstdlib>
#include <stdexcept>
#include <thread>

static std::string ler_env(const char* nome, const std::string& padrao) {
    const char* val = std::getenv(nome);
    return (val && *val) ? std::string(val) : padrao;
}

static int ler_env_int(const char* nome, int padrao) {
    const char* val = std::getenv(nome);
    return (val && *val) ? std::stoi(val) : padrao;
}

Config ler_config(int argc, char** argv) {
    Config cfg;
    cfg.porta        = ler_env_int("SERVIDOR_PORTA", cfg.porta);
    cfg.workers      = ler_env_int("SERVIDOR_WORKERS", cfg.workers);
    cfg.max_fila     = ler_env_int("SERVIDOR_MAX_FILA", cfg.max_fila);
    cfg.threads_http = ler_env_int("SERVIDOR_THREADS_HTTP", cfg.threads_http);
    cfg.pasta_dados  = ler_env("SERVIDOR_PASTA_DADOS", cfg.pasta_dados);
    cfg.pasta_logs   = ler_env("SERVIDOR_PASTA_LOGS", cfg.pasta_logs);
    cfg.modelos      = ler_env("SERVIDOR_MODELOS", cfg.modelos);

    for (int i = 1; i < argc; ++i) {
        std::string arg = argv[i];
        auto proximo = [&]() -> std::string {
            if (i + 1 >= argc) {
                throw std::invalid_argument("faltando valor para " + arg);
            }
            return argv[++i];
        };

        if (arg == "--port" || arg == "--porta") {
            cfg.porta = std::stoi(proximo());
        } else if (arg == "--workers") {
            cfg.workers = std::stoi(proximo());
        } else if (arg == "--max-queue" || arg == "--max-fila") {
            cfg.max_fila = std::stoi(proximo());
        } else if (arg == "--http-threads" || arg == "--threads-http") {
            cfg.threads_http = std::stoi(proximo());
        } else if (arg == "--data-dir" || arg == "--pasta-dados") {
            cfg.pasta_dados = proximo();
        } else if (arg == "--log-dir" || arg == "--pasta-logs") {
            cfg.pasta_logs = proximo();
        } else if (arg == "--modelos" || arg == "--models") {
            cfg.modelos = proximo();
        } else {
            throw std::invalid_argument("argumento desconhecido: " + arg);
        }
    }

    if (cfg.workers <= 0) {
        unsigned int hw = std::thread::hardware_concurrency();
        cfg.workers = std::max(1u, hw / 2);
    }
    if (cfg.threads_http < 4) {
        cfg.threads_http = 4;
    }
    return cfg;
}

