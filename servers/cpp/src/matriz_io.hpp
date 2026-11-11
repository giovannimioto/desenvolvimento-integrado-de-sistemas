#ifndef MATRIZ_IO_HPP
#define MATRIZ_IO_HPP

#include <string>
#include <Eigen/Dense>

// H e armazenada em RowMajor: o .bin gerado pelo NumPy (tofile) e C-contiguo, linha a linha.
using MatrizH = Eigen::Matrix<float, Eigen::Dynamic, Eigen::Dynamic, Eigen::RowMajor>;

MatrizH ler_matriz_bin(const std::string& caminho, long linhas, long colunas);
Eigen::VectorXf ler_vetor_bin(const std::string& caminho, long tamanho);
Eigen::MatrixXf ler_matriz_csv(const std::string& caminho, char separador = ',');
void salvar_vetor_csv(const std::string& caminho, const Eigen::VectorXf& vetor);

#endif

