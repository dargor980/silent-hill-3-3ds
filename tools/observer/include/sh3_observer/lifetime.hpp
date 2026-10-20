#pragma once

#include <array>
#include <cstdint>

namespace sh3::observer {
constexpr std::uint64_t lifetime_max_cycles = 60ULL * 294912000;
constexpr std::uint32_t lifetime_max_notices = 1000000;

struct LifetimeStamp {
  std::array<std::uint8_t, 16> session{};
  std::uint64_t epoch{}, serial{}, cycle{};
};
struct LifetimeTarget {
  std::uint32_t root{}, pool{}, object{}, vtable{}; // Physical EE RAM offsets.
};
struct LifetimePlan {
  LifetimeStamp begin{};
  LifetimeTarget target{};
  std::uint32_t limit{};
};
enum class LifetimeState : std::uint8_t { idle, armed, sealed, failed };
enum class LifetimeReason : std::uint8_t {
  none, plan, protocol, identity, epoch, sequence, cycle, budget, range,
  protected_write, reset, restore, remap, settings, lost, shutdown, cancelled
};
enum class LifetimeKind : std::uint8_t {
  write, checkpoint, finish, reset, restore, remap, settings, lost, shutdown, cancel
};
struct LifetimeNotice {
  LifetimeStamp stamp{};
  LifetimeKind kind{LifetimeKind::checkpoint};
  std::uint32_t offset{}, size{}; // Only write notices may have a range.
};
struct LifetimeReport {
  LifetimeState state{LifetimeState::idle};
  LifetimeReason reason{LifetimeReason::none};
  LifetimeStamp begin{}, last{};
  std::uint32_t accepted{}, writes{}, checkpoints{};
};

// Caller serializes ALL callbacks before their effects. This class authenticates
// neither that producer nor its coverage. Sealed means supplied notices only.
class LifetimeGuard final {
public:
  LifetimeGuard() = default;
  LifetimeGuard(const LifetimeGuard&) = delete;
  LifetimeGuard& operator=(const LifetimeGuard&) = delete;
  LifetimeGuard(LifetimeGuard&&) = delete;
  LifetimeGuard& operator=(LifetimeGuard&&) = delete;
  bool arm(const LifetimePlan&) noexcept;
  bool notify(const LifetimeNotice&) noexcept;
  LifetimeReport report() const noexcept { return report_; }
private:
  bool fail(LifetimeReason) noexcept;
  LifetimePlan plan_{};
  LifetimeReport report_{};
};
} // namespace sh3::observer
