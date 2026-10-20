#pragma once
// Private fault injection only. Never included in the clean candidate.
#include <atomic>
#include <chrono>
#include <cstdio>
#include <cstdlib>
#include <cstring>
#include <pthread.h>
namespace sh3_pc {
inline std::atomic<unsigned> sent{};
inline unsigned limit() noexcept {
  const char* value=std::getenv("SH3_PARTIAL_BYTES");
  if (value && !std::strcmp(value,"1")) return 1;
  if (value && !std::strcmp(value,"293")) return 293;
  std::abort();
}
inline void trace(const char* event, unsigned bytes=0) noexcept {
  const auto ns=std::chrono::duration_cast<std::chrono::nanoseconds>(
    std::chrono::steady_clock::now().time_since_epoch()).count();
  std::fprintf(stderr,"SH3_PC event=%s bytes=%u main=%d ns=%lld\n",
    event,bytes,pthread_main_np(),static_cast<long long>(ns));
  std::fflush(stderr);
}
}
