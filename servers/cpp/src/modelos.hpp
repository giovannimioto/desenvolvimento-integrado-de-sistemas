#ifndef MODELOS_HPP
#define MODELOS_HPP

#include "config.hpp"
#include "matriz_io.hpp"

#include <map>
#include <string>

struct Modelo {
    std::string nome;   // "30x30" ou "60x60"
    int lado;           // 30 ou 60
    int S, N;           // amostras e sensores
    MatrizH H;          // carregada uma unica vez; depois apenas leitura concorrente
};

using MapaModelos = std::map<std::string, Modelo>;

MapaModelos carregar_modelos(const Config& cfg);

#endif

