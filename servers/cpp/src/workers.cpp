#include "workers.hpp"

#include <exception>
#include <utility>

Resposta montar_resposta(const Pedido& pedido,
                         Relogio::time_point inicio,
                         Relogio::time_point fim,
                         Relogio::time_point recebido_em,
                         ResultadoReconstrucao& resultado) {
    Resposta resp;
    resp.client_id   = pedido.client_id;
    resp.signal_id   = pedido.signal_id;
    resp.algoritmo   = pedido.algoritmo;
    resp.modelo      = pedido.modelo;
    resp.started_at  = formatar_iso8601(inicio);
    resp.finished_at = formatar_iso8601(fim);
    resp.received_at = formatar_iso8601(recebido_em);
    resp.iterations  = resultado.iteracoes;
    resp.duration_ms = diferenca_ms(inicio, fim);
    resp.wait_ms     = diferenca_ms(recebido_em, inicio);
    resp.error       = resultado.erro_final;
    resp.f           = std::move(resultado.f);
    return resp;
}

void laco_worker(FilaJobs& fila,
                 const MapaModelos& modelos,
                 LogCsv& log,
                 Estatisticas& est) {
    while (auto job = fila.retirar()) {
        est.em_processamento++;
        try {
            const Modelo& m = modelos.at(job->pedido.modelo);
            const auto inicio = Relogio::now();
            ResultadoReconstrucao r = (job->pedido.algoritmo == "CGNE")
                                          ? cgne(m.H, job->pedido.g)
                                          : cgnr(m.H, job->pedido.g);
            const auto fim = Relogio::now();
            Resposta resp = montar_resposta(job->pedido, inicio, fim, job->recebido_em, r);
            log.registrar(resp);
            job->promessa.set_value(std::move(resp));
        } catch (...) {
            job->promessa.set_exception(std::current_exception());
        }
        est.em_processamento--;
        est.processados++;
    }
}

