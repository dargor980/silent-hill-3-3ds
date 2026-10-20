#pragma once
#include <array>
#include <cstddef>
#include <cstdint>

namespace sh3::observer {
enum class AdmissionCondition : std::uint8_t {
  cpu_thread, cpu_boundary, paused, implementations_settled,
  ee_interpreter, iop_interpreter, vu0_interpreter, vu1_interpreter,
  ee_cache_disabled, fastmem_disabled, mtvu_disabled, vif_dynarec_disabled,
  raintegration_disabled, pine_excluded, rdebug_excluded,
  gs_drained, vu_drained, other_writers_excluded, count
};
enum class AdmissionFact : std::uint8_t { unknown, satisfied, violated };
constexpr std::size_t admission_condition_count = static_cast<std::size_t>(AdmissionCondition::count);
static_assert(admission_condition_count < 32);
using AdmissionProfile = std::array<AdmissionFact, admission_condition_count>;
constexpr std::uint32_t admission_bit(AdmissionCondition condition) noexcept {
  const auto index = static_cast<unsigned>(condition);
  return index < admission_condition_count ? std::uint32_t{1} << index : 0;
}
struct AdmissionReport {
  std::uint32_t violated{}, unknown{};
  // Diagnostic only: even a clear report is not a capture capability or lock.
};
AdmissionReport assess_profile(const AdmissionProfile&) noexcept;
} // namespace sh3::observer
