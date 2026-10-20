#pragma once
#include <array>
#include <cstddef>
#include <cstdint>
#include <mach/message.h>
#include <sys/socket.h>

namespace sh3::observer {
struct MacOSPeerIdentity {
  std::uint32_t pid{}, euid{}, ruid{}, pid_version{};
  std::uint64_t birth_ns{};
  std::array<std::uint8_t, 32> token{};
};
struct MacOSPeerCalls {
  int (*option)(int, int, int, void*, socklen_t*);
  int (*info)(int, int, std::uint64_t, void*, int);
  int (*path)(audit_token_t*, void*, std::uint32_t);
};
MacOSPeerCalls macos_peer_calls() noexcept;
// Borrowed descriptor: caller owns and serializes it throughout both readings.
bool read_macos_peer(int, MacOSPeerIdentity&, MacOSPeerCalls = macos_peer_calls()) noexcept;
// Terminal release only: requires EOF, not a connected observation channel.
// Never use this identity to accept/publish a diagnostic response.
bool read_macos_released_peer(int, MacOSPeerIdentity&, MacOSPeerCalls = macos_peer_calls()) noexcept;
std::uint64_t read_macos_birth(int, MacOSPeerCalls = macos_peer_calls()) noexcept;
} // namespace sh3::observer
// Local ABI for the Python consumer, never an assertion received over the wire.
extern "C" int sh3_macos_peer_v1(int, std::uint8_t*, std::size_t) noexcept;
extern "C" std::uint64_t sh3_macos_birth_v1(int) noexcept;
