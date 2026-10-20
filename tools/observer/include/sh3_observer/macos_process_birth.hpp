#pragma once
#include "sh3_observer/process_birth.hpp"
#include <cstddef>

namespace sh3::observer {
// Internal seams for API error tests; no transport/client chooses these calls.
struct MacOSBirthCalls {
  int (*pid)();
  int (*info)(int, int, std::uint64_t, void*, int);
};
class MacOSBirthSource final : public BirthSource {
public:
  MacOSBirthSource() noexcept;
  explicit MacOSBirthSource(MacOSBirthCalls calls) noexcept : calls_(calls) {}
  bool read(BirthReading&) noexcept override;
private:
  MacOSBirthCalls calls_;
};
class MacOSNonceSource final : public NonceSource {
public:
  using Fill = int (*)(void*, std::size_t);
  MacOSNonceSource() noexcept;
  explicit MacOSNonceSource(Fill fill) noexcept : fill_(fill) {}
  bool fill(ProcessNonce&) noexcept override;
private:
  Fill fill_;
};
} // namespace sh3::observer
