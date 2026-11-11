#include "matriz_io.hpp"

#include <fstream>
#include <iomanip>
#include <sstream>
#include <stdexcept>
#include <vector>

MatrizH ler_matriz_bin(const std::string& caminho, long linhas, long colunas) {
    std::ifstream arquivo(caminho, std::ios::binary | std::ios::ate);
    if (!arquivo) {
        throw std::runtime_error("arquivo nao encontrado: " + caminho);
    }

    const std::streamsize bytes = linhas * colunas * static_cast<long>(sizeof(float));
    if (arquivo.tellg() != bytes) {
        throw std::runtime_error("tamanho inesperado em " + caminho);
    }

    arquivo.seekg(0);
    MatrizH H(linhas, colunas);
    arquivo.read(reinterpret_cast<char*>(H.data()), bytes);
    if (!arquivo) {
        throw std::runtime_error("falha na leitura de " + caminho);
    }
    return H;
}

Eigen::VectorXf ler_vetor_bin(const std::string& caminho, long tamanho) {
    std::ifstream arquivo(caminho, std::ios::binary | std::ios::ate);
    if (!arquivo) {
        throw std::runtime_error("arquivo nao encontrado: " + caminho);
    }

    const std::streamsize bytes = tamanho * static_cast<long>(sizeof(float));
    if (arquivo.tellg() != bytes) {
        throw std::runtime_error("tamanho inesperado em " + caminho);
    }

    arquivo.seekg(0);
    Eigen::VectorXf v(tamanho);
    arquivo.read(reinterpret_cast<char*>(v.data()), bytes);
    if (!arquivo) {
        throw std::runtime_error("falha na leitura de " + caminho);
    }
    return v;
}

Eigen::MatrixXf ler_matriz_csv(const std::string& caminho, char separador) {
    std::ifstream arquivo(caminho);
    if (!arquivo) {
        throw std::runtime_error("arquivo nao encontrado: " + caminho);
    }

    std::vector<std::vector<float>> linhas_lidas;
    std::string linha;
    while (std::getline(arquivo, linha)) {
        if (!linha.empty() && linha.back() == '\r') {
            linha.pop_back();
        }
        if (linha.empty()) {
            continue;
        }
        std::vector<float> valores;
        std::stringstream ss(linha);
        std::string celula;
        while (std::getline(ss, celula, separador)) {
            if (!celula.empty() && celula.back() == '\r') {
                celula.pop_back();
            }
            if (!celula.empty()) {
                valores.push_back(std::stof(celula));
            }
        }
        if (!valores.empty()) {
            if (!linhas_lidas.empty() && valores.size() != linhas_lidas.front().size()) {
                throw std::runtime_error("numero inconsistente de colunas em " + caminho);
            }
            linhas_lidas.push_back(std::move(valores));
        }
    }

    if (linhas_lidas.empty()) {
        throw std::runtime_error("CSV vazio: " + caminho);
    }

    const long n_linhas = static_cast<long>(linhas_lidas.size());
    const long n_colunas = static_cast<long>(linhas_lidas.front().size());
    Eigen::MatrixXf M(n_linhas, n_colunas);
    for (long i = 0; i < n_linhas; ++i) {
        for (long j = 0; j < n_colunas; ++j) {
            M(i, j) = linhas_lidas[i][j];
        }
    }
    return M;
}

void salvar_vetor_csv(const std::string& caminho, const Eigen::VectorXf& vetor) {
    std::ofstream arquivo(caminho);
    if (!arquivo) {
        throw std::runtime_error("nao foi possivel gravar " + caminho);
    }
    arquivo << std::setprecision(8);
    for (Eigen::Index i = 0; i < vetor.size(); ++i) {
        arquivo << vetor(i) << "\n";
    }
}

