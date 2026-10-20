#pragma once
// Validation only. Hold before Host dispatch; never block the CPU thread.
#include "sh3_observer/runtime_diagnostic_handoff.hpp"
#include <atomic>
#include <chrono>
#include <cstdio>
#include <cstdlib>
#include <cstring>
#include <functional>
#include <mutex>
#include <pthread.h>
namespace sh3_hc {
enum class Mode { late_cancel, late_deadline, duplicate_active, duplicate_retired };
inline Mode mode() {
  const char* value=std::getenv("SH3_HOST_CALLBACK_MODE");
  if (value && !std::strcmp(value,"late_cancel")) return Mode::late_cancel;
  if (value && !std::strcmp(value,"late_deadline")) return Mode::late_deadline;
  if (value && !std::strcmp(value,"duplicate_active")) return Mode::duplicate_active;
  if (value && !std::strcmp(value,"duplicate_retired")) return Mode::duplicate_retired;
  std::abort();
}
inline std::atomic<bool> held{};
inline std::mutex mutex;
inline std::function<void()> release;
inline std::weak_ptr<sh3::observer::RuntimeDiagnosticHandoff> weak;
inline thread_local unsigned ordinal{};
inline void trace(const char* event, unsigned value=0, int cpu=-1) noexcept {
  const auto ns=std::chrono::duration_cast<std::chrono::nanoseconds>(
    std::chrono::steady_clock::now().time_since_epoch()).count();
  std::fprintf(stderr,"SH3_HC event=%s value=%u ordinal=%u cpu=%d main=%d ns=%lld\n",
    event,value,ordinal,cpu,pthread_main_np(),static_cast<long long>(ns));
  std::fflush(stderr);
}
inline void remember(const std::shared_ptr<sh3::observer::RuntimeDiagnosticHandoff>& h) {
  std::lock_guard lock(mutex);weak=h;
}
inline void retain(std::function<void()> dispatch) {
  {std::lock_guard lock(mutex);if (release) std::abort();release=std::move(dispatch);}
  trace("held");held=true;
}
inline void after_io() {
  trace("io_destroyed");
  std::function<void()> dispatch;
  // std::function's moved-from state is valid but unspecified; clear the slot.
  {std::lock_guard lock(mutex);dispatch=std::move(release);release={};}
  if (dispatch) {trace("retained_release");dispatch();}
}
inline bool expired() {std::lock_guard lock(mutex);return weak.expired();}
}
