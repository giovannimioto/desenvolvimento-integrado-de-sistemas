#include "matriz_io.hpp"

#include <chrono>
#include <filesystem>
#include <iomanip>
#include <iostream>
#include <string>

namespace fs = std::filesystem;
using Relogio = std::chrono::steady_clock;

static double segundos_desde(Relogio::time_point inicio) {
    return std::chrono::duration<double>(Relogio::now() - inicio).count();
}

int main(int argc, char** argv) {
    const std::string pasta_fase2 = (argc > 1) ? argv[1] : "data/fase2";

    std::cout << std::fixed << std::setprecision(6);
    std::cout << "=== Fase 2: Validacao com Dados.zip (" << pasta_fase2 << ") ===\n";

    Eigen::MatrixXf M = ler_matriz_csv(pasta_fase2 + "/M.csv", ';');
    Eigen::MatrixXf N = ler_matriz_csv(pasta_fase2 + "/N.csv", ';');
    Eigen::MatrixXf a = ler_matriz_csv(pasta_fase2 + "/a.csv", ';');
    Eigen::MatrixXf MN_ref = ler_matriz_csv(pasta_fase2 + "/MN.csv", ';');
    Eigen::MatrixXf aM_ref = ler_matriz_csv(pasta_fase2 + "/aM.csv", ';');

    auto t0 = Relogio::now();
    Eigen::MatrixXf MN = M * N;
    double t_mn = segundos_desde(t0);
    float diff_mn = (MN - MN_ref).cwiseAbs().maxCoeff();

    t0 = Relogio::now();
    Eigen::MatrixXf aM = a * M;
    double t_am = segundos_desde(t0);
    float diff_am = (aM - aM_ref).cwiseAbs().maxCoeff();

    t0 = Relogio::now();
    Eigen::MatrixXf Ma = M * a.transpose();
    double t_ma = segundos_desde(t0);

    std::cout << "MN (" << MN.rows() << "x" << MN.cols() << "): diff_max = "
              << diff_mn << " | tempo = " << t_mn * 1e6 << " us\n";
    std::cout << "aM (" << aM.rows() << "x" << aM.cols() << "): diff_max = "
              << diff_am << " | tempo = " << t_am * 1e6 << " us\n";
    std::cout << "Ma (" << Ma.rows() << "x" << Ma.cols() << "): norma    = "
              << Ma.norm() << " | tempo = " << t_ma * 1e6 << " us\n";

    if (diff_mn > 1e-2f || diff_am > 1e-2f) {
        std::cerr << "ERRO: diferenca acima da tolerancia na Fase 2!\n";
        return 1;
    }

    fs::path caminho_h2 = fs::path(pasta_fase2).parent_path() / "H-2.bin";
    if (!fs::exists(caminho_h2)) {
        caminho_h2 = "data/H-2.bin";
    }
    if (fs::exists(caminho_h2)) {
        std::cout << "\n=== Cronometragem com H-2 (27904x900) ===\n";
        t0 = Relogio::now();
        MatrizH H2 = ler_matriz_bin(caminho_h2.string(), 27904, 900);
        std::cout << "Leitura H-2.bin: " << segundos_desde(t0) << " s\n";

        Eigen::VectorXf f = Eigen::VectorXf::Ones(900);

        t0 = Relogio::now();
        Eigen::MatrixXf HtH = H2.transpose() * H2;
        std::cout << "MN (H2^T * H2, " << HtH.rows() << "x" << HtH.cols() << "): "
                  << segundos_desde(t0) << " s (norma=" << HtH.norm() << ")\n";

        t0 = Relogio::now();
        MatrizH dois_H2 = 2.0f * H2;
        std::cout << "aM (2.0 * H2,  " << dois_H2.rows() << "x" << dois_H2.cols() << "): "
                  << segundos_desde(t0) << " s (norma=" << dois_H2.norm() << ")\n";

        t0 = Relogio::now();
        Eigen::VectorXf Hf = H2 * f;
        std::cout << "Ma (H2 * f,    " << Hf.size() << "x1):   "
                  << segundos_desde(t0) << " s (norma=" << Hf.norm() << ")\n";
    }

    return 0;
}

