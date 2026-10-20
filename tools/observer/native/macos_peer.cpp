#include "sh3_observer/macos_peer.hpp"
#include <algorithm>
#include <bsm/libbsm.h>
#include <cerrno>
#include <cstring>
#include <libproc.h>
#include <limits>
#include <poll.h>
#include <sys/proc_info.h>
#include <sys/un.h>
#include <unistd.h>

namespace sh3::observer {
namespace {
bool birth(int pid, MacOSPeerCalls calls, proc_bsdinfo& info, std::uint64_t& ns) noexcept {
  if (pid <= 0 || !calls.info || calls.info(pid, PROC_PIDTBSDINFO, 0, &info, sizeof(info)) != sizeof(info) ||
      info.pbi_pid != static_cast<std::uint32_t>(pid) || !info.pbi_start_tvsec ||
      info.pbi_start_tvusec >= 1000000) return false;
  constexpr auto max = std::numeric_limits<std::uint64_t>::max();
  if (info.pbi_start_tvsec > (max - info.pbi_start_tvusec * 1000) / 1000000000) return false;
  ns = info.pbi_start_tvsec * 1000000000 + info.pbi_start_tvusec * 1000;
  return true;
}
template<typename T> bool option(int fd, int level, int key, T& value, MacOSPeerCalls calls) noexcept {
  socklen_t size = sizeof(value);
  return calls.option && calls.option(fd, level, key, &value, &size) == 0 && size == sizeof(value);
}
bool socket_shape(int fd, MacOSPeerCalls calls) noexcept {
  if (fd < 0) return false;
  int type{}; if (!option(fd, SOL_SOCKET, SO_TYPE, type, calls) || type != SOCK_STREAM) return false;
  sockaddr_un address{}; socklen_t size = sizeof(address);
  if (::getsockname(fd, reinterpret_cast<sockaddr*>(&address), &size) != 0 || address.sun_family != AF_UNIX) return false;
  size = sizeof(address);
  if (::getpeername(fd, reinterpret_cast<sockaddr*>(&address), &size) != 0 || address.sun_family != AF_UNIX) return false;
  return true;
}
bool connected(int fd, MacOSPeerCalls calls) noexcept {
  if (!socket_shape(fd,calls)) return false;
  pollfd poller{fd, POLLIN | POLLOUT, 0};
  if (::poll(&poller, 1, 0) < 0 || (poller.revents & (POLLHUP | POLLERR | POLLNVAL))) return false;
  char byte{}; const auto n = ::recv(fd, &byte, 1, MSG_PEEK | MSG_DONTWAIT);
  return n > 0 || (n < 0 && (errno == EAGAIN || errno == EWOULDBLOCK));
}
bool released(int fd, MacOSPeerCalls calls) noexcept {
  if (!socket_shape(fd,calls)) return false;
  pollfd poller{fd,POLLIN,0};
  if (::poll(&poller,1,0)<0 || (poller.revents&(POLLERR|POLLNVAL))) return false;
  char byte{};
  return ::recv(fd,&byte,1,MSG_PEEK|MSG_DONTWAIT)==0;
}
bool once(int fd, MacOSPeerCalls calls, MacOSPeerIdentity& out, bool terminal=false) noexcept {
  int pid{}; audit_token_t token{}; uid_t uid{}; gid_t gid{};
  if (!(terminal ? released(fd,calls) : connected(fd,calls)) || !calls.path ||
      !option(fd,SOL_LOCAL,LOCAL_PEERPID,pid,calls) || pid <= 0 ||
      !option(fd,SOL_LOCAL,LOCAL_PEERTOKEN,token,calls) ||
      ::getpeereid(fd,&uid,&gid) != 0 || audit_token_to_pid(token) != pid ||
      audit_token_to_euid(token) != uid) return false;
  proc_bsdinfo info{}; std::uint64_t ns{};
  if (!birth(pid,calls,info,ns) || info.pbi_uid != uid || info.pbi_ruid != audit_token_to_ruid(token)) return false;
  char path[PROC_PIDPATHINFO_MAXSIZE]{};
  if (calls.path(&token,path,sizeof(path)) <= 0) return false;
  out = {static_cast<std::uint32_t>(pid),uid,info.pbi_ruid,
         static_cast<std::uint32_t>(audit_token_to_pidversion(token)),ns,{}};
  static_assert(sizeof(token) == 32);
  std::memcpy(out.token.data(), &token, sizeof(token));
  return true;
}
}
MacOSPeerCalls macos_peer_calls() noexcept { return {::getsockopt,::proc_pidinfo,::proc_pidpath_audittoken}; }
std::uint64_t read_macos_birth(int pid, MacOSPeerCalls calls) noexcept {
  proc_bsdinfo a{},b{}; std::uint64_t first{},last{};
  return birth(pid,calls,a,first) && birth(pid,calls,b,last) && first == last ? first : 0;
}
bool read_macos_peer(int fd, MacOSPeerIdentity& out, MacOSPeerCalls calls) noexcept {
  out = {};
  MacOSPeerIdentity a{}, b{};
  if (!once(fd,calls,a) || !once(fd,calls,b) || a.pid != b.pid || a.euid != b.euid ||
      a.ruid != b.ruid || a.pid_version != b.pid_version || a.birth_ns != b.birth_ns ||
      a.token != b.token) return false;
  out = a; return true;
}
bool read_macos_released_peer(int fd, MacOSPeerIdentity& out, MacOSPeerCalls calls) noexcept {
  out = {};
  MacOSPeerIdentity a{}, b{};
  if (!once(fd,calls,a,true) || !once(fd,calls,b,true) || a.pid != b.pid || a.euid != b.euid ||
      a.ruid != b.ruid || a.pid_version != b.pid_version || a.birth_ns != b.birth_ns ||
      a.token != b.token) return false;
  out = a; return true;
}
} // namespace sh3::observer
extern "C" int sh3_macos_peer_v1(int fd, std::uint8_t* out, std::size_t size) noexcept {
  if (!out || size != 56) return 0;
  std::fill_n(out,size,0); sh3::observer::MacOSPeerIdentity p;
  if (!sh3::observer::read_macos_peer(fd,p)) return 0;
  std::size_t offset{};
  const auto write = [&](std::uint64_t n, unsigned count) {
    for (unsigned i=0;i<count;++i) { out[offset++]=n&255; n>>=8; }
  };
  write(p.pid,4);write(p.euid,4);write(p.ruid,4);write(p.pid_version,4);write(p.birth_ns,8);
  std::copy(p.token.begin(),p.token.end(),out+offset);return 1;
}
extern "C" std::uint64_t sh3_macos_birth_v1(int pid) noexcept { return sh3::observer::read_macos_birth(pid); }
