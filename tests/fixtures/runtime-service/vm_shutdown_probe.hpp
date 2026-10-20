#pragma once
// Private validation only. Atomic phase observation never stalls CPU or DW.
#include <atomic>
#include <chrono>
#include <cstdio>
#include <pthread.h>
namespace sh3_vs {
inline std::atomic<bool> inventory{};
inline unsigned decision{}; // UI only: 1=No, 2=Yes.
inline void trace(const char* event, unsigned value=0) noexcept {
  const auto ns=std::chrono::duration_cast<std::chrono::nanoseconds>(
    std::chrono::steady_clock::now().time_since_epoch()).count();
  std::fprintf(stderr,"SH3_VS event=%s value=%u main=%d ns=%lld\n",
    event,value,pthread_main_np(),static_cast<long long>(ns));
  std::fflush(stderr);
}
struct InventoryScope {
  InventoryScope() { inventory=true; }
  ~InventoryScope() { inventory=false; }
};
}
