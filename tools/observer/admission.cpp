#include "sh3_observer/admission.hpp"

namespace sh3::observer {
AdmissionReport assess_profile(const AdmissionProfile& profile) noexcept {
  AdmissionReport report;
  for (std::size_t index = 0; index < profile.size(); ++index) {
    const auto bit = std::uint32_t{1} << index;
    switch (profile[index]) {
      case AdmissionFact::satisfied: break;
      case AdmissionFact::violated: report.violated |= bit; break;
      default: report.unknown |= bit; break;
    }
  }
  return report;
}
} // namespace sh3::observer
