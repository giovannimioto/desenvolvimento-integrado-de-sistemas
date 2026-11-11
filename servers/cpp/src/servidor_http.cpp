#include "servidor_http.hpp"

#include <httplib.h>
#include <json.hpp>

#include <atomic>
#include <exception>
#include <iostream>
#include <memory>
#include <utility>
#include <vector>

using json = nlohmann::json;

namespace {
std::atomic<httplib::Server*> g_servidor_ativo{nullptr};
std::atomic<bool> g_parada_solicitada{false};

void responder_json(httplib::Response& res, int status, const json& corpo) {
    res.status = status;
    res.set_content(corpo.dump(), "application/json; charset=utf-8");
}

json para_json(const Resposta& r) {
    std::vector<float> vetor_f(r.f.data(), r.f.data() + r.f.size());
    return json{
        {"client_id", r.client_id},
        {"signal_id", r.signal_id},
        {"algorithm", r.algoritmo},
        {"model", r.modelo},
        {"started_at", r.started_at},
        {"finished_at", r.finished_at},
        {"iterations", r.iterations},
        {"f", std::move(vetor_f)},
        {"server", "cpp"},
        {"duration_ms", r.duration_ms},
        {"wait_ms", r.wait_ms},
        {"error", r.error}
    };
}
}  // namespace

bool interpretar_pedido(const std::string& corpo_json,
                        const MapaModelos& modelos,
                        Pedido& saida,
                        std::string& erro) {
    json j = json::parse(corpo_json, nullptr, false);
    if (j.is_discarded() || !j.is_object()) {
        erro = "JSON invalido";
        return false;
    }

    for (const char* campo : {"client_id", "signal_id", "model", "algorithm"}) {
        if (!j.contains(campo) || !j[campo].is_string()) {
            erro = std::string("campo obrigatorio ausente ou invalido: ") + campo;
            return false;
        }
    }
    if (!j.contains("g") || !j["g"].is_array()) {
        erro = "campo 'g' deve ser um array numerico";
        return false;
    }

    saida.client_id = j["client_id"].get<std::string>();
    saida.signal_id = j["signal_id"].get<std::string>();
    saida.modelo    = j["model"].get<std::string>();
    saida.algoritmo = j["algorithm"].get<std::string>();

    if (saida.client_id.empty() || saida.signal_id.empty()) {
        erro = "client_id e signal_id nao podem ser vazios";
        return false;
    }

    auto it_mod = modelos.find(saida.modelo);
    if (it_mod == modelos.end()) {
        erro = "modelo desconhecido: " + saida.modelo;
        return false;
    }

    if (saida.algoritmo != "CGNE" && saida.algoritmo != "CGNR") {
        erro = "algoritmo desconhecido: " + saida.algoritmo;
        return false;
    }

    const auto& arr_g = j["g"];
    const Eigen::Index esperado = it_mod->second.H.rows();
    if (static_cast<Eigen::Index>(arr_g.size()) != esperado) {
        erro = "tamanho de g (" + std::to_string(arr_g.size()) +
               ") diferente do esperado (" + std::to_string(esperado) + ")";
        return false;
    }

    saida.g.resize(esperado);
    for (Eigen::Index i = 0; i < esperado; ++i) {
        if (!arr_g[static_cast<std::size_t>(i)].is_number()) {
            erro = "elemento nao numerico em g";
            return false;
        }
        saida.g(i) = arr_g[static_cast<std::size_t>(i)].get<float>();
    }
    return true;
}

void executar_servidor_http(const Config& cfg,
                            const MapaModelos& modelos,
                            FilaJobs& fila,
                            Estatisticas& est) {
    httplib::Server svr;
    svr.new_task_queue = [n = cfg.threads_http] { return new httplib::ThreadPool(n); };

    svr.Post("/reconstruir", [&](const httplib::Request& req, httplib::Response& res) {
        Pedido pedido;
        std::string erro;
        if (!interpretar_pedido(req.body, modelos, pedido, erro)) {
            responder_json(res, 400, {{"erro", erro}});
            return;
        }

        auto job = std::make_unique<Job>();
        job->pedido = std::move(pedido);
        job->recebido_em = Relogio::now();
        auto futuro = job->promessa.get_future();

        if (!fila.tentar_inserir(std::move(job))) {
            est.rejeitados++;
            res.set_header("Retry-After", "1");
            responder_json(res, 503, {{"erro", "fila cheia"}});
            return;
        }

        try {
            Resposta resp = futuro.get();
            responder_json(res, 200, para_json(resp));
        } catch (const std::exception& e) {
            responder_json(res, 500, {{"erro", e.what()}});
        }
    });

    svr.Get("/status", [&](const httplib::Request&, httplib::Response& res) {
        responder_json(res, 200, {
            {"queue_size", fila.tamanho()},
            {"workers", cfg.workers},
            {"processed", est.processados.load()},
            {"in_progress", est.em_processamento.load()},
            {"rejected", est.rejeitados.load()},
            {"max_queue", cfg.max_fila}
        });
    });

    g_servidor_ativo.store(&svr);
    if (g_parada_solicitada.load()) {
        g_servidor_ativo.store(nullptr);
        return;
    }

    std::cout << "[Servidor C++] Escutando em http://0.0.0.0:" << cfg.porta
              << " | workers=" << cfg.workers
              << " | max_queue=" << cfg.max_fila
              << " | http_threads=" << cfg.threads_http << std::endl;

    svr.listen("0.0.0.0", cfg.porta);
    g_servidor_ativo.store(nullptr);
}

void solicitar_parada_servidor_http() {
    g_parada_solicitada.store(true);
    if (httplib::Server* svr = g_servidor_ativo.load()) {
        svr->stop();
    }
}

