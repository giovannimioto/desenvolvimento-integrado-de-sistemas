#ifndef FILA_JOBS_HPP
#define FILA_JOBS_HPP

#include "tempo.hpp"

#include <Eigen/Dense>
#include <condition_variable>
#include <cstddef>
#include <future>
#include <memory>
#include <mutex>
#include <queue>
#include <string>

struct Pedido {
    std::string client_id;
    std::string signal_id;
    std::string modelo;
    std::string algoritmo;
    Eigen::VectorXf g;
};

struct Resposta {
    std::string client_id;
    std::string signal_id;
    std::string algoritmo;
    std::string modelo;
    std::string started_at;
    std::string finished_at;
    std::string received_at;
    int iterations = 0;
    double duration_ms = 0.0;
    double wait_ms = 0.0;
    float error = 0.0f;
    Eigen::VectorXf f;
};

struct Job {
    Pedido pedido;
    Relogio::time_point recebido_em;
    std::promise<Resposta> promessa;
};

class FilaJobs {
public:
    explicit FilaJobs(std::size_t capacidade_maxima = 0);  // 0 = ilimitada

    bool tentar_inserir(std::unique_ptr<Job> job);         // false se cheia -> HTTP 503
    std::unique_ptr<Job> retirar();                        // bloqueia; nullptr quando fechada e vazia
    void fechar();                                         // acorda todos os workers para encerrar
    std::size_t tamanho() const;

private:
    mutable std::mutex mutex_;
    std::condition_variable tem_job_;
    std::queue<std::unique_ptr<Job>> fila_;
    std::size_t capacidade_maxima_;
    bool fechada_ = false;
};

#endif

