#ifndef ESTATISTICAS_HPP
#define ESTATISTICAS_HPP

#include <atomic>

struct Estatisticas {
    std::atomic<long> processados{0};
    std::atomic<long> rejeitados{0};
    std::atomic<long> em_processamento{0};
};

#endif

