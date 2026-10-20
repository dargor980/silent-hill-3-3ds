#pragma once
#include "sh3_observer/diagnostic_delivery.hpp"

namespace sh3::observer {
class DiagnosticChannel : public DiagnosticDeliverySink {
public:
  // Sole IO owner. Same progress/wait contract as write; EOF is terminal.
  virtual bool read(std::uint8_t*, std::size_t, std::size_t&,
                    DiagnosticClock::Clock::duration maximum_wait) noexcept = 0;
  virtual bool connected() noexcept = 0;
  virtual bool close() noexcept = 0;
};
} // namespace sh3::observer
