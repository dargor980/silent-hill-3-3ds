#include "sh3_observer/macos_process_birth.hpp"
#include <libproc.h>
#include <sys/proc_info.h>
#include <sys/random.h>
#include <unistd.h>

namespace sh3::observer {
MacOSBirthSource::MacOSBirthSource() noexcept : calls_{::getpid, ::proc_pidinfo} {}
bool MacOSBirthSource::read(BirthReading& output) noexcept {
  output = {};
  if (!calls_.pid || !calls_.info) return false;
  const int pid = calls_.pid();
  if (pid <= 0) return false;
  proc_bsdinfo info{};
  const auto size = static_cast<int>(sizeof(info));
  if (calls_.info(pid, PROC_PIDTBSDINFO, 0, &info, size) != size ||
      info.pbi_pid != static_cast<std::uint32_t>(pid) || calls_.pid() != pid ||
      info.pbi_start_tvsec == 0 || info.pbi_start_tvusec >= 1000000) return false;
  output = {info.pbi_pid, info.pbi_start_tvsec, info.pbi_start_tvusec};
  return true;
}
MacOSNonceSource::MacOSNonceSource() noexcept : fill_(::getentropy) {}
bool MacOSNonceSource::fill(ProcessNonce& output) noexcept {
  output = {};
  if (!fill_ || fill_(output.data(), output.size()) != 0) {
    output = {};
    return false;
  }
  return true;
}
} // namespace sh3::observer
