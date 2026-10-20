#pragma once
#include <array>
#include <cstdint>

namespace sh3::observer {
using ProcessNonce = std::array<std::uint8_t, 16>;
struct BirthReading {
  std::uint32_t pid{};
  std::uint64_t seconds{}, microseconds{};
};
struct ProcessKey {
  std::uint32_t pid{};
  std::uint64_t birth_ns{};
  ProcessNonce nonce{};
};
bool same_process_key(const ProcessKey&, const ProcessKey&) noexcept;
class BirthSource {
public:
  virtual ~BirthSource() = default;
  virtual bool read(BirthReading&) noexcept = 0;
};
class NonceSource {
public:
  virtual ~NonceSource() = default;
  virtual bool fill(ProcessNonce&) noexcept = 0;
};
enum class BirthFailure : std::uint8_t { none, unavailable, invalid, entropy, changed, lost };
struct BirthResult {
  ProcessKey key{};
  BirthFailure failure{BirthFailure::none};
};
// One owner serializes this instance for the lifetime of ONE provider process.
// A key identifies that instance only, never an artifact, channel peer or VM.
class ProcessBirth final {
public:
  ProcessBirth(BirthSource& birth, NonceSource& nonce) noexcept : birth_(birth), nonce_(nonce) {}
  ProcessBirth(const ProcessBirth&) = delete;
  ProcessBirth& operator=(const ProcessBirth&) = delete;
  ProcessBirth(ProcessBirth&&) = delete;
  ProcessBirth& operator=(ProcessBirth&&) = delete;
  BirthResult sample() noexcept;
  void lose() noexcept;
private:
  BirthResult fail(BirthFailure) noexcept;
  BirthSource& birth_;
  NonceSource& nonce_;
  ProcessKey key_{};
  BirthFailure failure_{BirthFailure::none};
  bool ready_{};
};
} // namespace sh3::observer
