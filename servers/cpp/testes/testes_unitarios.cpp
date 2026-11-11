#include "algoritmos.hpp"
#include "fila_jobs.hpp"
#include "matriz_io.hpp"
#include "modelos.hpp"
#include "servidor_http.hpp"

#include <atomic>
#include <cassert>
#include <cmath>
#include <filesystem>
#include <fstream>
#include <iostream>
#include <set>
#include <stdexcept>
#include <thread>
#include <vector>

namespace fs = std::filesystem;

static void testar_bin_ida_e_volta() {
    const std::string caminho_m = "/tmp/teste_matriz_icms31.bin";
    const std::string caminho_v = "/tmp/teste_vetor_icms31.bin";

    MatrizH original(3, 4);
    original << 1.0f, 2.0f, 3.0f, 4.0f,
                5.0f, 6.0f, 7.0f, 8.0f,
                9.0f, 10.0f, 11.0f, 12.0f;
    {
        std::ofstream out(caminho_m, std::ios::binary);
        out.write(reinterpret_cast<const char*>(original.data()), 12 * sizeof(float));
    }

    MatrizH lida = ler_matriz_bin(caminho_m, 3, 4);
    assert((original - lida).cwiseAbs().maxCoeff() == 0.0f);

    bool falhou_tamanho = false;
    try {
        (void)ler_matriz_bin(caminho_m, 4, 4);
    } catch (const std::runtime_error&) {
        falhou_tamanho = true;
    }
    assert(falhou_tamanho);

    Eigen::VectorXf v_orig(4);
    v_orig << -1.5f, 0.0f, 2.25f, 100.0f;
    {
        std::ofstream out(caminho_v, std::ios::binary);
        out.write(reinterpret_cast<const char*>(v_orig.data()), 4 * sizeof(float));
    }
    Eigen::VectorXf v_lido = ler_vetor_bin(caminho_v, 4);
    assert((v_orig - v_lido).cwiseAbs().maxCoeff() == 0.0f);

    fs::remove(caminho_m);
    fs::remove(caminho_v);
    std::cout << "[OK] testar_bin_ida_e_volta\n";
}

static void testar_csv_crlf_e_ponto_virgula() {
    const std::string caminho = "/tmp/teste_csv_icms31.csv";
    {
        std::ofstream out(caminho, std::ios::binary);
        out << "1.5;2.5;3.5\r\n4.0;5.0;6.0\r\n";
    }
    Eigen::MatrixXf M = ler_matriz_csv(caminho, ';');
    assert(M.rows() == 2 && M.cols() == 3);
    assert(std::abs(M(0, 0) - 1.5f) < 1e-6f);
    assert(std::abs(M(1, 2) - 6.0f) < 1e-6f);
    fs::remove(caminho);
    std::cout << "[OK] testar_csv_crlf_e_ponto_virgula\n";
}

static void testar_fase2_dados_zip() {
    std::string pasta = "../../data/fase2";
    if (!fs::exists(pasta + "/M.csv")) {
        pasta = "data/fase2";
    }
    assert(fs::exists(pasta + "/M.csv"));

    Eigen::MatrixXf M = ler_matriz_csv(pasta + "/M.csv", ';');
    Eigen::MatrixXf N = ler_matriz_csv(pasta + "/N.csv", ';');
    Eigen::MatrixXf a = ler_matriz_csv(pasta + "/a.csv", ';');
    Eigen::MatrixXf MN_ref = ler_matriz_csv(pasta + "/MN.csv", ';');
    Eigen::MatrixXf aM_ref = ler_matriz_csv(pasta + "/aM.csv", ';');

    Eigen::MatrixXf MN = M * N;
    Eigen::MatrixXf aM = a * M;
    Eigen::MatrixXf Ma = M * a.transpose();

    assert(MN.rows() == 10 && MN.cols() == 10);
    assert(aM.rows() == 1 && aM.cols() == 10);
    assert(Ma.rows() == 10 && Ma.cols() == 1);
    assert((MN - MN_ref).cwiseAbs().maxCoeff() < 1e-2f);
    assert((aM - aM_ref).cwiseAbs().maxCoeff() < 1e-2f);
    std::cout << "[OK] testar_fase2_dados_zip\n";
}

static void testar_cgne_cgnr_sintetico_e_borda() {
    MatrizH H_peq = MatrizH::Identity(20, 10);
    Eigen::VectorXf g_zero = Eigen::VectorXf::Zero(20);
    auto r_cgne_zero = cgne(H_peq, g_zero);
    auto r_cgnr_zero = cgnr(H_peq, g_zero);
    assert(r_cgne_zero.iteracoes == 0 && !r_cgne_zero.f.hasNaN() && r_cgne_zero.f.norm() == 0.0f);
    assert(r_cgnr_zero.iteracoes == 0 && !r_cgnr_zero.f.hasNaN() && r_cgnr_zero.f.norm() == 0.0f);

    srand(42);
    Eigen::MatrixXf A = Eigen::MatrixXf::Random(200, 50);
    MatrizH H = A;
    for (int j = 0; j < 50; ++j) {
        H(j, j) += 5.0f;
    }
    Eigen::VectorXf f_real = Eigen::VectorXf::Random(50);
    Eigen::VectorXf g = H * f_real;

    Eigen::VectorXf f_qr = Eigen::MatrixXf(H).colPivHouseholderQr().solve(g);

    auto res_cgnr = cgnr(H, g, 50, 1e-6f);
    float erro_rel_cgnr = (res_cgnr.f - f_qr).norm() / f_qr.norm();
    assert(erro_rel_cgnr < 1e-3f);

    MatrizH H_quad = H.topRows(50);
    Eigen::VectorXf g_quad = H_quad * f_real;
    auto res_cgne = cgne(H_quad, g_quad, 80, 1e-6f);
    float erro_rel_cgne = (res_cgne.f - f_real).norm() / f_real.norm();
    assert(erro_rel_cgne < 1e-3f);

    float residuo_anterior = g.norm();
    for (int k = 1; k <= 10; ++k) {
        auto passo = cgnr(H, g, k, 0.0f);
        float residuo_atual = (g - H * passo.f).norm();
        assert(residuo_atual <= residuo_anterior + 1e-4f);
        residuo_anterior = residuo_atual;
    }

    std::cout << "[OK] testar_cgne_cgnr_sintetico_e_borda\n";
}

static void testar_fila_jobs_limitada_e_concorrente() {
    FilaJobs fila_lim(2);
    assert(fila_lim.tentar_inserir(std::make_unique<Job>()));
    assert(fila_lim.tentar_inserir(std::make_unique<Job>()));
    assert(fila_lim.tamanho() == 2);
    assert(!fila_lim.tentar_inserir(std::make_unique<Job>()));
    auto j1 = fila_lim.retirar();
    assert(j1 != nullptr);
    assert(fila_lim.tamanho() == 1);
    fila_lim.fechar();
    auto j2 = fila_lim.retirar();
    assert(j2 != nullptr);
    assert(fila_lim.retirar() == nullptr);

    FilaJobs fila_ilim(0);
    for (int i = 0; i < 1000; ++i) {
        auto job = std::make_unique<Job>();
        job->pedido.signal_id = std::to_string(i);
        assert(fila_ilim.tentar_inserir(std::move(job)));
    }
    assert(fila_ilim.tamanho() == 1000);
    fila_ilim.fechar();
    for (int i = 0; i < 1000; ++i) {
        assert(fila_ilim.retirar() != nullptr);
    }
    assert(fila_ilim.retirar() == nullptr);

    FilaJobs fila_conc(0);
    std::mutex mutex_ids;
    std::set<std::string> ids_consumidos;
    std::vector<std::thread> consumidores;
    for (int c = 0; c < 4; ++c) {
        consumidores.emplace_back([&] {
            while (auto job = fila_conc.retirar()) {
                std::lock_guard<std::mutex> trava(mutex_ids);
                ids_consumidos.insert(job->pedido.signal_id);
            }
        });
    }

    std::vector<std::thread> produtores;
    for (int p = 0; p < 4; ++p) {
        produtores.emplace_back([&, p] {
            for (int k = 0; k < 50; ++k) {
                auto job = std::make_unique<Job>();
                job->pedido.signal_id = "p" + std::to_string(p) + "-k" + std::to_string(k);
                assert(fila_conc.tentar_inserir(std::move(job)));
            }
        });
    }
    for (auto& t : produtores) t.join();
    fila_conc.fechar();
    for (auto& t : consumidores) t.join();
    assert(ids_consumidos.size() == 200);

    std::cout << "[OK] testar_fila_jobs_limitada_e_concorrente\n";
}

static void testar_interpretar_pedido() {
    MapaModelos modelos;
    modelos.emplace("30x30", Modelo{"30x30", 30, 4, 1, MatrizH::Zero(4, 2)});

    Pedido p;
    std::string erro;

    // 1. JSON quebrado
    assert(!interpretar_pedido("{quebrado", modelos, p, erro));

    // 2. Modelo desconhecido
    assert(!interpretar_pedido(
        R"({"client_id":"c1","signal_id":"s1","model":"99x99","algorithm":"CGNE","g":[1,2,3,4]})",
        modelos, p, erro));

    // 3. Algoritmo desconhecido
    assert(!interpretar_pedido(
        R"({"client_id":"c1","signal_id":"s1","model":"30x30","algorithm":"OUTRO","g":[1,2,3,4]})",
        modelos, p, erro));

    // 4. Tamanho de g errado
    assert(!interpretar_pedido(
        R"({"client_id":"c1","signal_id":"s1","model":"30x30","algorithm":"CGNE","g":[1,2,3]})",
        modelos, p, erro));

    // 5. Pedido valido
    assert(interpretar_pedido(
        R"({"client_id":"c1","signal_id":"s1","model":"30x30","algorithm":"CGNR","g":[1.0,2.0,3.0,4.0]})",
        modelos, p, erro));
    assert(p.client_id == "c1" && p.signal_id == "s1" && p.modelo == "30x30" && p.algoritmo == "CGNR");
    assert(p.g.size() == 4 && std::abs(p.g(3) - 4.0f) < 1e-6f);

    std::cout << "[OK] testar_interpretar_pedido\n";
}

int main() {
    testar_bin_ida_e_volta();
    testar_csv_crlf_e_ponto_virgula();
    testar_fase2_dados_zip();
    testar_cgne_cgnr_sintetico_e_borda();
    testar_fila_jobs_limitada_e_concorrente();
    testar_interpretar_pedido();
    std::cout << "Todos os testes unitarios passaram.\n";
    return 0;
}
