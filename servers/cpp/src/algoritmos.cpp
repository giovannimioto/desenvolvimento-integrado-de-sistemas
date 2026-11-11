#include "algoritmos.hpp"

#include <cmath>
#include <stdexcept>
#include <utility>

ResultadoReconstrucao cgne(const MatrizH& H, const Eigen::VectorXf& g,
                           int max_iter, float tolerancia) {
    Eigen::VectorXf f = Eigen::VectorXf::Zero(H.cols());
    Eigen::VectorXf r = g;
    Eigen::VectorXf p = H.transpose() * r;
    float rr = r.squaredNorm();
    float erro = 0.0f;
    int i = 0;

    if (rr == 0.0f) {
        return {f, 0, 0.0f};
    }

    while (i < max_iter) {
        const float pp = p.squaredNorm();
        if (pp == 0.0f) {
            break;
        }

        const float alpha = rr / pp;
        f.noalias() += alpha * p;
        Eigen::VectorXf r_novo = r - alpha * (H * p);
        const float rr_novo = r_novo.squaredNorm();
        const float beta = rr_novo / rr;
        p = H.transpose() * r_novo + beta * p;

        erro = std::abs(std::sqrt(rr_novo) - std::sqrt(rr));
        r = std::move(r_novo);
        rr = rr_novo;
        ++i;

        if (erro < tolerancia) {
            break;
        }
    }
    return {f, i, erro};
}

ResultadoReconstrucao cgnr(const MatrizH& H, const Eigen::VectorXf& g,
                           int max_iter, float tolerancia) {
    Eigen::VectorXf f = Eigen::VectorXf::Zero(H.cols());
    Eigen::VectorXf r = g;
    Eigen::VectorXf z = H.transpose() * r;
    Eigen::VectorXf p = z;
    float zz = z.squaredNorm();
    float norm_r = r.norm();
    float erro = 0.0f;
    int i = 0;

    if (norm_r == 0.0f || zz == 0.0f) {
        return {f, 0, 0.0f};
    }

    while (i < max_iter) {
        Eigen::VectorXf w = H * p;
        const float ww = w.squaredNorm();
        if (ww == 0.0f) {
            break;
        }

        const float alpha = zz / ww;
        f.noalias() += alpha * p;
        Eigen::VectorXf r_novo = r - alpha * w;
        Eigen::VectorXf z_novo = H.transpose() * r_novo;
        const float zz_novo = z_novo.squaredNorm();
        const float beta = zz_novo / zz;
        p = z_novo + beta * p;

        const float norm_r_novo = r_novo.norm();
        erro = std::abs(norm_r_novo - norm_r);
        r = std::move(r_novo);
        z = std::move(z_novo);
        zz = zz_novo;
        norm_r = norm_r_novo;
        ++i;

        if (erro < tolerancia) {
            break;
        }
    }
    return {f, i, erro};
}

Eigen::VectorXf aplicar_ganho(const Eigen::VectorXf& g, int S, int N) {
    if (g.size() != static_cast<Eigen::Index>(S) * N) {
        throw std::invalid_argument("tamanho de g incompativel com S * N");
    }
    Eigen::VectorXf g_ganho(g.size());
    for (int c = 0; c < N; ++c) {
        for (int l = 1; l <= S; ++l) {
            const float lf = static_cast<float>(l);
            const float gamma = 100.0f + 0.05f * lf * std::sqrt(lf);
            const int idx = c * S + (l - 1);
            g_ganho(idx) = g(idx) * gamma;
        }
    }
    return g_ganho;
}

