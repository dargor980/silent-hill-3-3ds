#include "sh3_observer/platform_diagnostic.hpp"
#include <algorithm>
#include <limits>

namespace sh3::observer {
namespace {
constexpr std::array<std::uint8_t, 8> request_magic{'S','H','3','P','D','Q','0','2'};
constexpr std::array<std::uint8_t, 8> response_magic{'S','H','3','P','D','R','0','2'};
template <std::size_t N> bool nonzero(const std::array<std::uint8_t, N>& value) noexcept {
  return std::any_of(value.begin(), value.end(), [](auto byte) { return byte != 0; });
}
bool counter(std::uint64_t value) noexcept {
  return value != 0 && value != std::numeric_limits<std::uint64_t>::max();
}
bool valid_request(const DiagnosticRequest& value) noexcept {
  return nonzero(value.challenge) && counter(value.sequence);
}
AdmissionFact normalize(AdmissionFact fact) noexcept {
  return fact == AdmissionFact::satisfied || fact == AdmissionFact::violated
    ? fact : AdmissionFact::unknown;
}
bool valid_epochs(const DiagnosticEpochs& e, const AdmissionProfile& facts) noexcept {
  if (e.host == 0 && e.pine == 0 && e.vu == 0 && e.gs == 0)
    return std::all_of(facts.begin(), facts.end(), [](auto f) {
      return normalize(f) == AdmissionFact::unknown;
    });
  return counter(e.host) && counter(e.pine) && counter(e.vu) && counter(e.gs);
}
bool valid_inventory(const PlatformInventoryResult& r, const DiagnosticExpectation& e) noexcept {
  return r.failure == PlatformInventoryFailure::none && r.profile == e.profile &&
    r.scope == IdentityScope::application_headers && r.platform_assumed &&
    r.process.pid > 0 && r.process.pid <= 0x7fffffff && r.process.birth_ns != 0 &&
    nonzero(r.process.nonce) && nonzero(r.file_objects) && nonzero(r.classified_images) &&
    r.policy_evidence == e.policy_evidence && r.application_evidence == e.application_evidence &&
    r.platform_evidence == e.platform_evidence && counter(r.loader_revision) &&
    r.application_images > 0 && r.application_images <= image_capacity &&
    r.platform_images <= image_capacity - r.application_images;
}
class Writer {
public:
  explicit Writer(DiagnosticBytes& bytes) noexcept : bytes_(bytes) {}
  void integer(std::uint64_t value, std::size_t count) noexcept {
    for (std::size_t i = 0; i < count; ++i) { bytes_[pos_++] = value & 255; value >>= 8; }
  }
  template <std::size_t N> void array(const std::array<std::uint8_t, N>& value) noexcept {
    for (const auto byte : value) bytes_[pos_++] = byte;
  }
private:
  DiagnosticBytes& bytes_;
  std::size_t pos_{};
};
void header(Writer& w, const DiagnosticRequest& request, bool observed,
            DiagnosticRejection reason) noexcept {
  w.array(response_magic);
  w.integer(observed ? 1 : 2, 1); w.integer(observed ? 2 : 0, 1);
  w.integer(observed ? 1 : 0, 1); w.integer(observed ? 1 : 0, 1);
  w.integer(static_cast<std::uint8_t>(reason), 1); w.integer(0, 3);
  w.array(request.challenge); w.integer(request.sequence, 8);
}
}
bool decode_diagnostic_request(const std::uint8_t* bytes, std::size_t size,
                               DiagnosticRequest& out) noexcept {
  out = {};
  if (!bytes || size != diagnostic_request_size ||
      !std::equal(request_magic.begin(), request_magic.end(), bytes)) return false;
  DiagnosticRequest candidate;
  std::copy_n(bytes + 8, candidate.challenge.size(), candidate.challenge.begin());
  for (std::size_t i = 0; i < 8; ++i) candidate.sequence |= std::uint64_t{bytes[24 + i]} << (8 * i);
  if (!valid_request(candidate)) return false;
  out = candidate;
  return true;
}
bool valid_diagnostic_expectation(const DiagnosticExpectation& e) noexcept {
  return e.profile == IdentityProfile::macos_platform_slices_v2 &&
    nonzero(e.policy_evidence) && nonzero(e.application_evidence) && nonzero(e.platform_evidence);
}
bool encode_platform_diagnostic(const DiagnosticExpectation& expectation,
                                const DiagnosticRequest& request,
                                const PlatformInventoryResult& inventory,
                                const AdmissionProfile& facts, const DiagnosticEpochs& epochs,
                                DiagnosticBytes& out) noexcept {
  out = {};
  if (!valid_diagnostic_expectation(expectation) || !valid_request(request) ||
      !valid_inventory(inventory, expectation) || !valid_epochs(epochs, facts)) return false;
  Writer w(out);
  header(w, request, true, DiagnosticRejection::none);
  w.integer(inventory.process.pid, 4); w.integer(inventory.process.birth_ns, 8);
  w.array(inventory.process.nonce); w.array(inventory.file_objects); w.array(inventory.classified_images);
  w.array(inventory.policy_evidence); w.array(inventory.application_evidence); w.array(inventory.platform_evidence);
  w.integer(inventory.loader_revision, 8);
  w.integer(inventory.application_images, 4); w.integer(inventory.platform_images, 4);
  for (const auto fact : facts) w.integer(static_cast<std::uint8_t>(normalize(fact)), 1);
  w.integer(epochs.host, 8); w.integer(epochs.pine, 8); w.integer(epochs.vu, 8); w.integer(epochs.gs, 8);
  return true;
}
bool encode_diagnostic_rejection(const DiagnosticRequest& request, DiagnosticRejection reason,
                                 DiagnosticBytes& out) noexcept {
  out = {};
  if (!valid_request(request) || reason < DiagnosticRejection::configuration ||
      reason > DiagnosticRejection::unavailable) return false;
  Writer w(out);
  header(w, request, false, reason);
  return true;
}
} // namespace sh3::observer
