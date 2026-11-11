#include "log_csv.hpp"
#include "tempo.hpp"

#include <filesystem>
#include <iomanip>
#include <stdexcept>

namespace fs = std::filesystem;

LogCsv::LogCsv(const std::string& pasta_logs) {
    fs::create_directories(pasta_logs);
    caminho_ = pasta_logs + "/reconstrucoes_" + carimbo_arquivo_atual() + ".csv";
    arquivo_.open(caminho_, std::ios::out | std::ios::trunc);
    if (!arquivo_) {
        throw std::runtime_error("nao foi possivel criar o log CSV: " + caminho_);
    }
    arquivo_ << "client_id,signal_id,algorithm,model,started_at,finished_at,"
                "iterations,received_at,wait_ms,duration_ms,error\n";
    arquivo_.flush();
}

void LogCsv::registrar(const Resposta& r) {
    std::lock_guard<std::mutex> trava(mutex_);
    arquivo_ << r.client_id << ","
             << r.signal_id << ","
             << r.algoritmo << ","
             << r.modelo << ","
             << r.started_at << ","
             << r.finished_at << ","
             << r.iterations << ","
             << r.received_at << ","
             << std::fixed << std::setprecision(3) << r.wait_ms << ","
             << std::fixed << std::setprecision(3) << r.duration_ms << ","
             << std::scientific << std::setprecision(6) << r.error << "\n";
    arquivo_.flush();
}

