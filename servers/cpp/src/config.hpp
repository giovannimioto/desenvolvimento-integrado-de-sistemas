#ifndef CONFIG_HPP
#define CONFIG_HPP

#include <string>

struct Config {
    int porta = 8080;
    int workers = 0;              // 0 -> hardware_concurrency()/2 (minimo 1)
    int max_fila = 0;             // 0 = ilimitada (sem controle); > 0 = rejeita com 503
    int threads_http = 128;       // pool de threads HTTP do cpp-httplib
    std::string pasta_dados = "data";
    std::string pasta_logs  = "logs/cpp";
    std::string modelos     = "30x30,60x60";
};

// Prioridade: argumento de linha de comando > variavel de ambiente > padrao.
Config ler_config(int argc, char** argv);

#endif

