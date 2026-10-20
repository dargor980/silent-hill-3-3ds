#pragma once
#include "sh3_observer/admission.hpp"
#include "sh3_observer/platform_inventory.hpp"

namespace sh3::observer {
constexpr std::size_t diagnostic_request_size = 32;
constexpr std::size_t diagnostic_response_size = 294;
using DiagnosticBytes = std::array<std::uint8_t, diagnostic_response_size>;
struct DiagnosticRequest {
  std::array<std::uint8_t, 16> challenge{};
  std::uint64_t sequence{};
};
// Launcher-owned, never supplied or selected by the remote request.
struct DiagnosticExpectation {
  IdentityProfile profile{IdentityProfile::unknown};
  Sha256 policy_evidence{}, application_evidence{}, platform_evidence{};
};
struct DiagnosticEpochs {
  std::uint64_t host{}, pine{}, vu{}, gs{};
};
enum class DiagnosticRejection : std::uint8_t {
  none, configuration, inventory, identity_changed, peer_lost, deadline,
  cancelled, protocol, lifecycle, unavailable
};
bool decode_diagnostic_request(const std::uint8_t*, std::size_t, DiagnosticRequest&) noexcept;
bool valid_diagnostic_expectation(const DiagnosticExpectation&) noexcept;
// Pure serialization, NOT attestation, peer verification, or a capture capability.
// Runtime facts must be sampled/bound by the caller; missing epochs allow only unknown facts.
bool encode_platform_diagnostic(const DiagnosticExpectation&, const DiagnosticRequest&,
                                const PlatformInventoryResult&, const AdmissionProfile&,
                                const DiagnosticEpochs&, DiagnosticBytes&) noexcept;
bool encode_diagnostic_rejection(const DiagnosticRequest&, DiagnosticRejection,
                                 DiagnosticBytes&) noexcept;
} // namespace sh3::observer
