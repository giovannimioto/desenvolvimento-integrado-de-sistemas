#ifndef TEMPO_HPP
#define TEMPO_HPP

#include <chrono>
#include <string>

// Usa steady_clock (monotonico) para todas as medicoes de tempo e converte para ISO-8601
// a partir de uma ancora inicial do system_clock, evitando saltos de NTP/WSL2.
using Relogio = std::chrono::steady_clock;

std::string formatar_iso8601(Relogio::time_point tp);
std::string carimbo_arquivo_atual();
double diferenca_ms(Relogio::time_point inicio, Relogio::time_point fim);

#endif
