#pragma once
#include "sh3_observer/diagnostic_channel.hpp"
#include "sh3_observer/macos_peer.hpp"
#include <atomic>
#include <thread>

namespace sh3::observer {
// Adopts a connected Unix socket. No aliases; only its creating thread may do
// IO/close/destroy. Expected identity comes from the trusted local launcher.
class MacOSDiagnosticSink final : public DiagnosticChannel {
public:
  MacOSDiagnosticSink(int owned_socket, MacOSPeerIdentity expected) noexcept;
  ~MacOSDiagnosticSink() override;
  MacOSDiagnosticSink(const MacOSDiagnosticSink&) = delete;
  MacOSDiagnosticSink& operator=(const MacOSDiagnosticSink&) = delete;
  bool write(const std::uint8_t*, std::size_t, std::size_t&,
             DiagnosticClock::Clock::duration) noexcept override;
  bool read(std::uint8_t*, std::size_t, std::size_t&,
            DiagnosticClock::Clock::duration) noexcept override;
  bool connected() noexcept override;
  bool close() noexcept override;
  // Terminal IO-only phase after the last reply. EOF is remote release, not
  // proof that the consumer published the frame. Never permits another request.
  DiagnosticRejection await_release(DiagnosticClock::Clock::time_point deadline,
                                    const std::atomic<bool>& cancelled) noexcept;
private:
  bool configure() noexcept;
  bool peer() noexcept;
  bool fail() noexcept;
  int fd_, owner_pid_;
  const std::thread::id owner_thread_;
  const MacOSPeerIdentity expected_;
  std::atomic<bool> failed_{};
  bool configured_{}, close_ok_{true};
};
} // namespace sh3::observer
