#include "modelos.hpp"

#include <chrono>
#include <iomanip>
#include <iostream>
#include <sstream>
#include <stdexcept>

MapaModelos carregar_modelos(const Config& cfg) {
    MapaModelos mapa;
    std::stringstream ss(cfg.modelos);
    std::string item;

    while (std::getline(ss, item, ',')) {
        if (item.empty()) {
            continue;
        }
        const auto t0 = std::chrono::steady_clock::now();
        if (item == "30x30") {
            const std::string arq = cfg.pasta_dados + "/H-2.bin";
            MatrizH H = ler_matriz_bin(arq, 27904, 900);
            const double s = std::chrono::duration<double>(std::chrono::steady_clock::now() - t0).count();
            const double mb = (27904.0 * 900.0 * sizeof(float)) / (1024.0 * 1024.0);
            std::cout << std::fixed << std::setprecision(2)
                      << "[Modelos] 30x30 (H-2, 27904x900, " << mb << " MB) carregado em "
                      << s << " s\n";
            mapa.emplace("30x30", Modelo{"30x30", 30, 436, 64, std::move(H)});
        } else if (item == "60x60") {
            const std::string arq = cfg.pasta_dados + "/H-1.bin";
            MatrizH H = ler_matriz_bin(arq, 50816, 3600);
            const double s = std::chrono::duration<double>(std::chrono::steady_clock::now() - t0).count();
            const double mb = (50816.0 * 3600.0 * sizeof(float)) / (1024.0 * 1024.0);
            std::cout << std::fixed << std::setprecision(2)
                      << "[Modelos] 60x60 (H-1, 50816x3600, " << mb << " MB) carregado em "
                      << s << " s\n";
            mapa.emplace("60x60", Modelo{"60x60", 60, 794, 64, std::move(H)});
        } else {
            throw std::invalid_argument("modelo desconhecido na configuracao: " + item);
        }
    }

    if (mapa.empty()) {
        throw std::runtime_error("nenhum modelo foi carregado");
    }
    return mapa;
}

