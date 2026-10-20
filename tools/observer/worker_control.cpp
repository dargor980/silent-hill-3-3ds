#include "sh3_observer/worker_control.hpp"

namespace sh3::observer {
void ControlWakeup::notify() noexcept {
  if (!pending_.exchange(true, std::memory_order_acq_rel)) signal_.release();
}
bool ControlWakeup::try_wait() noexcept {
  if (!signal_.try_acquire()) return false;
  pending_.exchange(false, std::memory_order_acq_rel);
  return true;
}
bool ControlWakeup::wait_until(Clock::time_point deadline) noexcept {
  if (!signal_.try_acquire_until(deadline)) return false;
  pending_.exchange(false, std::memory_order_acq_rel);
  return true;
}
bool WorkerControl::valid(Token t) noexcept {
  return t.generation != 0 && t.id != 0 && t.id <= max_request_id;
}
std::uint64_t WorkerControl::pack(Token t, Phase p) noexcept {
  return (std::uint64_t(t.generation) << 32) | (std::uint64_t(t.id) << 3) | std::uint64_t(p);
}
WorkerControl::Token WorkerControl::token(std::uint64_t word) noexcept {
  return {std::uint32_t(word >> 32), std::uint32_t(word) >> 3};
}
WorkerControl::Phase WorkerControl::phase(std::uint64_t word) noexcept {
  return Phase(word & 7);
}
bool WorkerControl::start(std::uint32_t generation) noexcept {
  auto old = word_.load(std::memory_order_acquire);
  if (!generation || generation <= token(old).generation || phase(old) != Phase::offline) return false;
  if (!word_.compare_exchange_strong(old, pack({generation, 0}, Phase::running),
                                    std::memory_order_acq_rel, std::memory_order_acquire)) return false;
  owner_wakeup_.notify();
  return true;
}
WorkerControl::StopResult WorkerControl::stop(std::uint32_t generation) noexcept {
  auto old = word_.load(std::memory_order_acquire);
  if (!generation || token(old).generation != generation) return StopResult::stale;
  if (phase(old) == Phase::offline) return StopResult::stopped;
  if (phase(old) == Phase::held) return StopResult::retained;
  if (!word_.compare_exchange_strong(old, pack(token(old), Phase::offline),
                                    std::memory_order_acq_rel, std::memory_order_acquire)) return StopResult::retry;
  owner_wakeup_.notify();
  return StopResult::stopped;
}
bool WorkerControl::request(Token t) noexcept {
  if (!valid(t)) return false;
  auto old = word_.load(std::memory_order_acquire);
  const auto previous = token(old);
  if (previous.generation != t.generation || t.id <= previous.id || phase(old) != Phase::running) return false;
  if (!word_.compare_exchange_strong(old, pack(t, Phase::requested),
                                    std::memory_order_acq_rel, std::memory_order_acquire)) return false;
  worker_wakeup_.notify();
  return true;
}
WorkerControl::Token WorkerControl::pending(std::uint32_t generation) const noexcept {
  const auto word = word_.load(std::memory_order_acquire);
  if (token(word).generation != generation || phase(word) != Phase::requested) return {};
  return token(word);
}
bool WorkerControl::acknowledge(Token t) noexcept {
  if (!valid(t)) return false;
  auto expected = pack(t, Phase::requested);
  if (!word_.compare_exchange_strong(expected, pack(t, Phase::held),
                                    std::memory_order_acq_rel, std::memory_order_acquire)) return false;
  owner_wakeup_.notify();
  return true;
}
bool WorkerControl::release(Token t) noexcept {
  if (!valid(t)) return false;
  auto old = word_.load(std::memory_order_acquire);
  // The only transition that can defeat a matching CAS and leave this token
  // active is the worker's requested->held. A second CAS retires that state.
  for (unsigned attempt = 0; attempt < 2; ++attempt) {
    if (token(old) != t || (phase(old) != Phase::requested && phase(old) != Phase::held)) return false;
    if (word_.compare_exchange_strong(old, pack(t, Phase::running),
                                     std::memory_order_acq_rel, std::memory_order_acquire)) {
      worker_wakeup_.notify();
      return true;
    }
  }
  return false;
}
WorkerControl::Status WorkerControl::status(Token t) const noexcept {
  if (!valid(t)) return Status::invalid;
  const auto word = word_.load(std::memory_order_acquire);
  if (token(word) != t) return Status::invalid;
  switch (phase(word)) {
    case Phase::offline: return Status::offline;
    case Phase::running: return Status::released;
    case Phase::requested: return Status::pending;
    case Phase::held: return Status::held;
  }
  return Status::invalid;
}
WorkerControl::Lifecycle WorkerControl::lifecycle() const noexcept {
  const auto word = word_.load(std::memory_order_acquire);
  return {token(word).generation, phase(word) != Phase::offline};
}
} // namespace sh3::observer
