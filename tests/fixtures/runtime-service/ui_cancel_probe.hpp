#pragma once
// Private validation only: observes phases without stopping IO, CPU or DW.
#include <atomic>
#include <chrono>
#include <cstdio>
#include <cstdlib>
#include <cstring>
#include <pthread.h>
namespace sh3_uc {
inline std::atomic<unsigned> phase{};
inline void trace(const char* event, unsigned value = 0) noexcept {
  const auto ns = std::chrono::duration_cast<std::chrono::nanoseconds>(
    std::chrono::steady_clock::now().time_since_epoch()).count();
  std::fprintf(stderr, "SH3_UC event=%s phase=%u main=%d ns=%lld\n",
    event, value, pthread_main_np(), static_cast<long long>(ns));
  std::fflush(stderr);
}
struct PhaseScope {
  explicit PhaseScope(unsigned value) noexcept { phase.store(value); }
  ~PhaseScope() { phase.store(0); }
};
} // namespace sh3_uc
