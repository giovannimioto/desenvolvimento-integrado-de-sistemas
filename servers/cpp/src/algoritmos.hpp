#ifndef ALGORITMOS_HPP
#define ALGORITMOS_HPP

#include "matriz_io.hpp"

struct ResultadoReconstrucao {
    Eigen::VectorXf f;
    int iteracoes;
    float erro_final;
};

// CGNE: para quando | ||r_{i+1}||_2 - ||r_i||_2 | < tolerancia ou ao atingir max_iter.
ResultadoReconstrucao cgne(const MatrizH& H, const Eigen::VectorXf& g,
                           int max_iter = 10, float tolerancia = 1e-4f);

// CGNR: minimiza ||g - H*f||_2 nas equacoes normais sem formar H^T*H explicitamente.
ResultadoReconstrucao cgnr(const MatrizH& H, const Eigen::VectorXf& g,
                           int max_iter = 10, float tolerancia = 1e-4f);

// Aplica o ganho de sinal gamma_l = 100 + (1/20)*l*sqrt(l), l = 1..S, em cada coluna c = 1..N.
Eigen::VectorXf aplicar_ganho(const Eigen::VectorXf& g, int S, int N);

#endif

