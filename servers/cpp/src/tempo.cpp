#include "tempo.hpp"

#include <ctime>
#include <iomanip>
#include <sstream>

namespace {
const auto g_ancora_sistema = std::chrono::system_clock::now();
const auto g_ancora_estavel = Relogio::now();

std::chrono::system_clock::time_point para_system_clock(Relogio::time_point tp) {
    const auto delta = std::chrono::duration_cast<std::chrono::system_clock::duration>(
        tp - g_ancora_estavel
    );
    return g_ancora_sistema + delta;
}

std::tm converter_hora_local(std::time_t t) {
    std::tm tm_local{};
#ifdef _WIN32
    localtime_s(&tm_local, &t);
#else
    localtime_r(&t, &tm_local);
#endif
    return tm_local;
}
}  // namespace

std::string formatar_iso8601(Relogio::time_point tp) {
    const auto tp_sis = para_system_clock(tp);
    const auto duracao = tp_sis.time_since_epoch();
    const auto segundos = std::chrono::duration_cast<std::chrono::seconds>(duracao);
    const auto ms = std::chrono::duration_cast<std::chrono::milliseconds>(duracao - segundos).count();

    const std::time_t t = std::chrono::system_clock::to_time_t(tp_sis);
    const std::tm tm_local = converter_hora_local(t);

    char fuso[16] = {0};
    std::strftime(fuso, sizeof(fuso), "%z", &tm_local);
    std::string fuso_str(fuso);
    if (fuso_str.size() == 5) {
        fuso_str.insert(3, ":");  // ex: -0300 -> -03:00
    }

    std::ostringstream oss;
    oss << std::put_time(&tm_local, "%Y-%m-%dT%H:%M:%S")
        << "." << std::setw(3) << std::setfill('0') << (ms < 0 ? 0 : ms)
        << fuso_str;
    return oss.str();
}

std::string carimbo_arquivo_atual() {
    const auto tp_sis = para_system_clock(Relogio::now());
    const std::time_t t = std::chrono::system_clock::to_time_t(tp_sis);
    const std::tm tm_local = converter_hora_local(t);
    std::ostringstream oss;
    oss << std::put_time(&tm_local, "%Y%m%d-%H%M%S");
    return oss.str();
}

double diferenca_ms(Relogio::time_point inicio, Relogio::time_point fim) {
    return std::chrono::duration<double, std::milli>(fim - inicio).count();
}
