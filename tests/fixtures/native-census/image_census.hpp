#pragma once
#include <array>
#include <cstddef>
#include <cstdint>

namespace sh3::observer::probe {
inline constexpr std::size_t census_capacity = 4096;
inline constexpr std::size_t census_event_budget = 16384;
inline constexpr std::size_t production_boundary = 1024;
enum class CensusFailure { none, duplicate, unknown_remove, null_address, capacity, event_budget };
enum class BoundaryKind { not_reached, new_address, duplicate, null_address };
struct CensusObservation {
  std::size_t events{}, adds{}, removes{}, active{}, peak{};
  std::size_t boundary_event{};
  std::uintptr_t boundary_address{};
  BoundaryKind boundary_kind{};
  CensusFailure failure{};
};
// Pure diagnostic state. The owner serializes events and observations.
class ImageCensus final {
public:
  void add(std::uintptr_t address) noexcept {
    if (!begin(true)) return;
    const auto found = find(address);
    if (state_.active == production_boundary && !state_.boundary_event) {
      state_.boundary_event = state_.events; state_.boundary_address = address;
      state_.boundary_kind = !address ? BoundaryKind::null_address :
        found < state_.active ? BoundaryKind::duplicate : BoundaryKind::new_address;
    }
    if (!address) { state_.failure = CensusFailure::null_address; return; }
    if (found < state_.active) { state_.failure = CensusFailure::duplicate; return; }
    if (state_.active == census_capacity) { state_.failure = CensusFailure::capacity; return; }
    addresses_[state_.active++] = address;
    if (state_.active > state_.peak) state_.peak = state_.active;
  }
  void remove(std::uintptr_t address) noexcept {
    if (!begin(false)) return;
    if (!address) { state_.failure = CensusFailure::null_address; return; }
    const auto found = find(address);
    if (found == state_.active) { state_.failure = CensusFailure::unknown_remove; return; }
    addresses_[found] = addresses_[--state_.active]; addresses_[state_.active] = 0;
  }
  CensusObservation observation() const noexcept { return state_; }
private:
  bool begin(bool added) noexcept {
    if (state_.failure != CensusFailure::none) return false;
    if (state_.events == census_event_budget) { state_.failure = CensusFailure::event_budget; return false; }
    ++state_.events;
    if (added) ++state_.adds; else ++state_.removes;
    return true;
  }
  std::size_t find(std::uintptr_t address) const noexcept {
    for (std::size_t i=0; i<state_.active; ++i) if (addresses_[i]==address) return i;
    return state_.active;
  }
  std::array<std::uintptr_t,census_capacity> addresses_{};
  CensusObservation state_{};
};
}
