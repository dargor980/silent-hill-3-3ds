#pragma once
#include "sh3_observer/lifetime.hpp"
#include <cstdint>

namespace sh3::observer {
// The RAM anchor is supplied by the host adapter. No host pointer is dereferenced.
class PhysicalWrites final {
public:
  PhysicalWrites(LifetimeGuard& guard, std::uint64_t ram_base) noexcept
    : guard_(guard), ram_base_(ram_base) {}
  PhysicalWrites(const PhysicalWrites&) = delete;
  PhysicalWrites& operator=(const PhysicalWrites&) = delete;
  bool write(std::uint64_t address, std::uint64_t size, std::uint64_t cycle) noexcept;
  bool unknown(std::uint64_t cycle) noexcept;
  bool lifecycle(LifetimeKind kind, std::uint64_t cycle) noexcept;
private:
  LifetimeNotice notice(std::uint64_t cycle, LifetimeKind kind) const noexcept;
  LifetimeGuard& guard_;
  const std::uint64_t ram_base_;
};

// Own the guard and bridge longer than this binding; do not access them concurrently.
// This serializes notifications, NOT the memory effects that follow the callbacks.
class WriteBinding final {
public:
  explicit WriteBinding(PhysicalWrites&) noexcept;
  ~WriteBinding();
  WriteBinding(const WriteBinding&) = delete;
  WriteBinding& operator=(const WriteBinding&) = delete;
  bool connected() const noexcept { return connected_; }
private:
  bool connected_{};
};
void before_host_write(std::uint64_t address, std::uint64_t size, std::uint64_t cycle) noexcept;
void before_untracked_write(std::uint64_t cycle) noexcept;
// Epoch survives binding changes and VM state restoration. Zero means exhausted.
// Neither this read nor the notification mutex authorizes concurrent arming.
std::uint64_t host_epoch() noexcept;
void before_lifecycle(LifetimeKind kind, std::uint64_t cycle) noexcept;
} // namespace sh3::observer
