#include "algoritmos.hpp"
#include "matriz_io.hpp"

#include <chrono>
#include <filesystem>
#include <iomanip>
#include <iostream>
#include <stdexcept>
#include <string>

namespace fs = std::filesystem;
using Relogio = std::chrono::steady_clock;

int main(int argc, char** argv) {
    std::string modelo = "30x30";
    std::string algoritmo = "CGNE";
    std::string caminho_sinal;
    std::string caminho_saida;
    std::string pasta_dados;
    bool usar_ganho = false;

    for (int i = 1; i < argc; ++i) {
        std::string arg = argv[i];
        if (arg == "--modelo" && i + 1 < argc) {
            modelo = argv[++i];
        } else if (arg == "--algoritmo" && i + 1 < argc) {
            algoritmo = argv[++i];
        } else if (arg == "--sinal" && i + 1 < argc) {
            caminho_sinal = argv[++i];
        } else if (arg == "--saida" && i + 1 < argc) {
            caminho_saida = argv[++i];
        } else if (arg == "--pasta-dados" && i + 1 < argc) {
            pasta_dados = argv[++i];
        } else if (arg == "--ganho") {
            usar_ganho = true;
        } else {
            throw std::invalid_argument("argumento desconhecido: " + arg);
        }
    }

    if (caminho_sinal.empty()) {
        std::cerr << "Uso: reconstruir_offline --modelo <30x30|60x60> --algoritmo <CGNE|CGNR> "
                     "--sinal <caminho.bin> [--ganho] [--saida <f.csv>]\n";
        return 1;
    }

    if (pasta_dados.empty()) {
        fs::path p = fs::path(caminho_sinal).parent_path();
        pasta_dados = p.empty() ? "data" : p.string();
    }

    long linhas = 0, colunas = 0;
    int S = 0, N = 64;
    std::string arquivo_h;
    if (modelo == "30x30") {
        linhas = 27904;
        colunas = 900;
        S = 436;
        arquivo_h = pasta_dados + "/H-2.bin";
    } else if (modelo == "60x60") {
        linhas = 50816;
        colunas = 3600;
        S = 794;
        arquivo_h = pasta_dados + "/H-1.bin";
    } else {
        throw std::invalid_argument("modelo invalido: " + modelo);
    }

    MatrizH H = ler_matriz_bin(arquivo_h, linhas, colunas);
    Eigen::VectorXf g = ler_vetor_bin(caminho_sinal, linhas);
    if (usar_ganho) {
        g = aplicar_ganho(g, S, N);
    }

    const auto inicio = Relogio::now();
    ResultadoReconstrucao res;
    if (algoritmo == "CGNE") {
        res = cgne(H, g);
    } else if (algoritmo == "CGNR") {
        res = cgnr(H, g);
    } else {
        throw std::invalid_argument("algoritmo invalido: " + algoritmo);
    }
    const double duracao_ms =
        std::chrono::duration<double, std::milli>(Relogio::now() - inicio).count();

    if (!caminho_saida.empty()) {
        salvar_vetor_csv(caminho_saida, res.f);
    }

    std::cout << std::fixed << std::setprecision(6)
              << "modelo=" << modelo
              << " algoritmo=" << algoritmo
              << " iteracoes=" << res.iteracoes
              << " erro=" << res.erro_final
              << " tempo_ms=" << duracao_ms
              << " norma_f=" << res.f.norm() << "\n";
    return 0;
}

