#include "sh3_observer/macos_diagnostic_sink.hpp"
#include <algorithm>
#include <cerrno>
#include <fcntl.h>
#include <poll.h>
#include <unistd.h>

namespace sh3::observer {
MacOSDiagnosticSink::MacOSDiagnosticSink(int fd, MacOSPeerIdentity expected) noexcept
  : fd_(fd), owner_pid_(::getpid()), owner_thread_(std::this_thread::get_id()), expected_(expected) {}
MacOSDiagnosticSink::~MacOSDiagnosticSink() { close(); }
bool MacOSDiagnosticSink::fail() noexcept { failed_ = true; return false; }
bool MacOSDiagnosticSink::peer() noexcept {
  MacOSPeerIdentity p;
  return !failed_ && read_macos_peer(fd_,p) && p.pid == expected_.pid &&
    p.birth_ns == expected_.birth_ns && p.euid == expected_.euid && p.ruid == expected_.ruid &&
    p.pid_version == expected_.pid_version && p.token == expected_.token;
}
bool MacOSDiagnosticSink::configure() noexcept {
  if (::getpid() != owner_pid_ || std::this_thread::get_id() != owner_thread_) return fail();
  if (!peer()) return fail();
  if (!configured_) {
    const int flags = ::fcntl(fd_,F_GETFL); const int one = 1;
    if (flags < 0 || ::fcntl(fd_,F_SETFL,flags|O_NONBLOCK) != 0 ||
        ::setsockopt(fd_,SOL_SOCKET,SO_NOSIGPIPE,&one,sizeof(one)) != 0) return fail();
    configured_ = true;
  }
  return true;
}
bool MacOSDiagnosticSink::connected() noexcept {
  if (!configure()) return false;
  std::uint8_t byte{};
  const auto count=::recv(fd_,&byte,1,MSG_PEEK);
  if (count<0 && errno!=EAGAIN && errno!=EWOULDBLOCK && errno!=EINTR) return fail();
  return (count!=0 && peer()) || fail();
}
bool MacOSDiagnosticSink::read(std::uint8_t* bytes, std::size_t size, std::size_t& received,
                              DiagnosticClock::Clock::duration wait) noexcept {
  received=0;
  if (!bytes || !size || size>diagnostic_request_size || wait<=decltype(wait)::zero() ||
      wait>std::chrono::milliseconds(20) || !configure()) return fail();
  pollfd descriptor{fd_,POLLIN,0};
  const auto ready=::poll(&descriptor,1,static_cast<int>(std::chrono::duration_cast<std::chrono::milliseconds>(wait).count()));
  if ((ready<0 && errno!=EINTR) || (descriptor.revents & (POLLERR|POLLHUP|POLLNVAL))) return fail();
  if (!peer()) return fail();
  if (ready<=0 || !(descriptor.revents & POLLIN)) return true;
  const auto count=::recv(fd_,bytes,size,0);
  if (count<0 && (errno==EAGAIN || errno==EWOULDBLOCK || errno==EINTR)) return peer() || fail();
  if (count<=0 || static_cast<std::size_t>(count)>size || !peer()) return fail();
  received=static_cast<std::size_t>(count);
  return true;
}
bool MacOSDiagnosticSink::write(const std::uint8_t* bytes, std::size_t size, std::size_t& written,
                               DiagnosticClock::Clock::duration wait) noexcept {
  written = 0;
  if (!bytes || !size || size > diagnostic_response_size || wait <= decltype(wait)::zero() ||
      wait > std::chrono::milliseconds(20) || !configure()) return fail();
  // Floor the millisecond timeout: poll must never extend the caller's budget.
  pollfd descriptor{fd_,POLLOUT,0};
  const auto ready = ::poll(&descriptor,1,static_cast<int>(std::chrono::duration_cast<std::chrono::milliseconds>(wait).count()));
  if ((ready < 0 && errno != EINTR) || (descriptor.revents & (POLLERR|POLLHUP|POLLNVAL))) return fail();
  if (!peer()) return fail();
  if (ready <= 0 || !(descriptor.revents & POLLOUT)) return true;
  const auto count = ::send(fd_,bytes,size,0);
  if (count < 0 && (errno == EAGAIN || errno == EWOULDBLOCK || errno == EINTR))
    return peer() || fail();
  if (count <= 0 || static_cast<std::size_t>(count) > size || !peer()) return fail();
  written = static_cast<std::size_t>(count);
  return true;
}
bool MacOSDiagnosticSink::close() noexcept {
  if (::getpid() == owner_pid_ && std::this_thread::get_id() != owner_thread_) return fail();
  if (fd_ >= 0) {
    const int fd = fd_; fd_ = -1;
    if (::close(fd) != 0) close_ok_ = false;
  }
  failed_ = true;
  return close_ok_;
}
DiagnosticRejection MacOSDiagnosticSink::await_release(
    DiagnosticClock::Clock::time_point deadline, const std::atomic<bool>& cancelled) noexcept {
  using Clock = DiagnosticClock::Clock;
  using Reason = DiagnosticRejection;
  const auto finish = [&](Reason reason) { failed_ = true; return reason; };
  auto last = Clock::now();
  if (cancelled.load()) return finish(Reason::cancelled);
  if (deadline <= last) return finish(Reason::deadline);
  if (deadline > last + std::chrono::seconds(2)) return finish(Reason::configuration);
  if (failed_ || fd_<0 || ::getpid()!=owner_pid_ || std::this_thread::get_id()!=owner_thread_)
    return finish(Reason::peer_lost);
  // A completed write already authenticated/configured this exact owned fd.
  // Do not ask the ordinary connected-reader to accept EOF as an observation.
  if (!configured_ && !configure()) return finish(Reason::peer_lost);
  const auto released_peer = [&]() noexcept {
    MacOSPeerIdentity p;
    return read_macos_released_peer(fd_,p) && p.pid==expected_.pid &&
      p.birth_ns==expected_.birth_ns && p.euid==expected_.euid && p.ruid==expected_.ruid &&
      p.pid_version==expected_.pid_version && p.token==expected_.token;
  };
  const auto checkpoint = [&]() noexcept {
    const auto now = Clock::now();
    if (cancelled.load()) return Reason::cancelled;
    if (now < last) return Reason::unavailable;
    if (now >= deadline) return Reason::deadline;
    last = now;
    return Reason::none;
  };
  for (;;) {
    if (const auto reason = checkpoint(); reason != Reason::none) return finish(reason);
    const bool same = peer();
    const bool ended = !same && released_peer();
    if (const auto reason = checkpoint(); reason != Reason::none) return finish(reason);
    if (ended) return finish(Reason::none);
    if (!same) return finish(Reason::peer_lost);
    std::uint8_t byte{};
    const auto count = ::recv(fd_, &byte, 1, MSG_PEEK);
    const int error = errno;
    if (const auto reason = checkpoint(); reason != Reason::none) return finish(reason);
    if (count == 0) {
      const bool verified = released_peer();
      if (const auto reason = checkpoint(); reason != Reason::none) return finish(reason);
      return finish(verified ? Reason::none : Reason::peer_lost);
    }
    if (count > 0) return finish(Reason::protocol);
    if (error != EAGAIN && error != EWOULDBLOCK && error != EINTR)
      return finish(Reason::peer_lost);
    const auto wait = std::min(deadline-last, Clock::duration(std::chrono::milliseconds(20)));
    pollfd descriptor{fd_, POLLIN, 0};
    const auto ready = ::poll(&descriptor, 1,
      static_cast<int>(std::chrono::duration_cast<std::chrono::milliseconds>(wait).count()));
    const int poll_error = errno;
    if (const auto reason = checkpoint(); reason != Reason::none) return finish(reason);
    if ((ready < 0 && poll_error != EINTR) || (descriptor.revents & (POLLERR|POLLNVAL)))
      return finish(Reason::peer_lost);
    // POLLHUP is examined by recv on the next iteration, with budget and peer
    // checks. Normal read/write still treat it as failure.
  }
}
} // namespace sh3::observer
