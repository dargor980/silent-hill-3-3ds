#include "sh3_observer/process_birth.hpp"
#include <limits>

namespace sh3::observer {
namespace {
bool valid_birth(const BirthReading& value, std::uint64_t& ns) noexcept {
  constexpr auto maximum = std::numeric_limits<std::uint64_t>::max();
  if (value.pid == 0 || value.pid > 0x7fffffff || value.seconds == 0 ||
      value.microseconds >= 1000000 || value.seconds > maximum / 1000000000) return false;
  const auto seconds = value.seconds * 1000000000;
  const auto micros = value.microseconds * 1000;
  if (seconds > maximum - micros) return false;
  ns = seconds + micros;
  return true;
}
bool nonzero(const ProcessNonce& nonce) noexcept {
  for (const auto byte : nonce) if (byte != 0) return true;
  return false;
}
}
bool same_process_key(const ProcessKey& a, const ProcessKey& b) noexcept {
  return a.pid == b.pid && a.birth_ns == b.birth_ns && a.nonce == b.nonce;
}
BirthResult ProcessBirth::fail(BirthFailure reason) noexcept {
  if (failure_ == BirthFailure::none) failure_ = reason;
  key_ = {};
  return {{}, failure_};
}
void ProcessBirth::lose() noexcept { (void)fail(BirthFailure::lost); }
BirthResult ProcessBirth::sample() noexcept {
  if (failure_ != BirthFailure::none) return {{}, failure_};
  BirthReading first{}, last{};
  std::uint64_t first_ns{}, last_ns{};
  if (!birth_.read(first)) return fail(BirthFailure::unavailable);
  if (!valid_birth(first, first_ns)) return fail(BirthFailure::invalid);
  if (ready_ && (key_.pid != first.pid || key_.birth_ns != first_ns))
    return fail(BirthFailure::changed);
  ProcessNonce candidate = key_.nonce;
  if (!ready_ && (!nonce_.fill(candidate) || !nonzero(candidate)))
    return fail(BirthFailure::entropy);
  if (!birth_.read(last)) return fail(BirthFailure::unavailable);
  if (!valid_birth(last, last_ns)) return fail(BirthFailure::invalid);
  if (first.pid != last.pid || first_ns != last_ns) return fail(BirthFailure::changed);
  key_ = {first.pid, first_ns, candidate};
  ready_ = true;
  return {key_, BirthFailure::none};
}
} // namespace sh3::observer
