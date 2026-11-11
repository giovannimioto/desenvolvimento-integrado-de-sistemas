#include "fila_jobs.hpp"

FilaJobs::FilaJobs(std::size_t capacidade_maxima)
    : capacidade_maxima_(capacidade_maxima) {}

bool FilaJobs::tentar_inserir(std::unique_ptr<Job> job) {
    {
        std::lock_guard<std::mutex> trava(mutex_);
        if (fechada_) {
            return false;
        }
        if (capacidade_maxima_ > 0 && fila_.size() >= capacidade_maxima_) {
            return false;
        }
        fila_.push(std::move(job));
    }
    tem_job_.notify_one();
    return true;
}

std::unique_ptr<Job> FilaJobs::retirar() {
    std::unique_lock<std::mutex> trava(mutex_);
    tem_job_.wait(trava, [this] { return fechada_ || !fila_.empty(); });
    if (fila_.empty()) {
        return nullptr;
    }
    auto job = std::move(fila_.front());
    fila_.pop();
    return job;
}

void FilaJobs::fechar() {
    {
        std::lock_guard<std::mutex> trava(mutex_);
        fechada_ = true;
    }
    tem_job_.notify_all();
}

std::size_t FilaJobs::tamanho() const {
    std::lock_guard<std::mutex> trava(mutex_);
    return fila_.size();
}

