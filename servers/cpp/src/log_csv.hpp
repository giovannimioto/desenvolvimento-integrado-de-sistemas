#ifndef LOG_CSV_HPP
#define LOG_CSV_HPP

#include "fila_jobs.hpp"

#include <fstream>
#include <mutex>
#include <string>

class LogCsv {
public:
    explicit LogCsv(const std::string& pasta_logs);

    void registrar(const Resposta& resp);
    const std::string& caminho_arquivo() const { return caminho_; }

private:
    std::string caminho_;
    std::ofstream arquivo_;
    std::mutex mutex_;
};

#endif

