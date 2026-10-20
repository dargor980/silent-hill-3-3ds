#include "sh3_observer/macos_image_identity.hpp"
#include <atomic>
#include <fcntl.h>
#include <libproc.h>
#include <mach-o/dyld.h>
#include <pthread.h>
#include <sys/proc_info.h>
#include <sys/stat.h>
#include <unistd.h>
#include <type_traits>
#include <utility>

namespace sh3::observer {
namespace {
bool from_stat(const struct stat& s, FileObject& result) noexcept {
  if (!S_ISREG(s.st_mode) || s.st_size <= 0 || s.st_mtimespec.tv_nsec < 0 || s.st_ctimespec.tv_nsec < 0 ||
      s.st_mtimespec.tv_nsec >= 1000000000 || s.st_ctimespec.tv_nsec >= 1000000000) return false;
  result = {static_cast<std::uint32_t>(s.st_dev), s.st_ino, static_cast<std::uint64_t>(s.st_size),
    s.st_mtimespec.tv_sec, s.st_ctimespec.tv_sec, static_cast<std::uint32_t>(s.st_mtimespec.tv_nsec),
    static_cast<std::uint32_t>(s.st_ctimespec.tv_nsec)};
  return valid_file(result);
}
struct Events {
  std::atomic<int> owner{0};
  std::atomic<bool> failed{false};
  pthread_once_t once = PTHREAD_ONCE_INIT;
  pthread_mutex_t mutex = PTHREAD_MUTEX_INITIALIZER;
  ImageLedger ledger{};
};
static_assert(std::is_trivially_destructible_v<Events>);
static_assert(std::atomic<int>::is_always_lock_free && std::atomic<bool>::is_always_lock_free);
// No destructor/unregister: dyld may call back during process teardown.
Events& registry() noexcept { static Events state; return state; }
void event(std::uintptr_t address, bool added) noexcept {
  auto& events = registry();
  if (events.owner.load() != getpid() || events.failed.load()) return;
  if (pthread_mutex_lock(&events.mutex) != 0) { events.failed.store(true); return; }
  if (added) events.ledger.add(address); else events.ledger.remove(address);
  if (pthread_mutex_unlock(&events.mutex) != 0) events.failed.store(true);
}
void add_image(const mach_header* header, intptr_t) { event(reinterpret_cast<std::uintptr_t>(header), true); }
void remove_image(const mach_header* header, intptr_t) { event(reinterpret_cast<std::uintptr_t>(header), false); }
void register_events() {
  _dyld_register_func_for_remove_image(remove_image);
  _dyld_register_func_for_add_image(add_image);
}
}
MacOSFileAnchor::MacOSFileAnchor(std::string path) noexcept : path_(std::move(path)) {
  if (path_.empty() || path_.front() != '/' || path_.find('\0') != std::string::npos) return;
  descriptor_ = open(path_.c_str(), O_RDONLY | O_CLOEXEC | O_NOFOLLOW | O_NONBLOCK);
  if (descriptor_ < 0) return;
  struct stat s{};
  if (fstat(descriptor_, &s) != 0 || !from_stat(s, original_)) return;
  failed_ = false;
  FileObject ignored{};
  (void)read(ignored);
}
MacOSFileAnchor::~MacOSFileAnchor() { if (descriptor_ >= 0) close(descriptor_); }
bool MacOSFileAnchor::read(FileObject& output) noexcept {
  output = {};
  if (failed_) return false;
  struct stat held{}, named{};
  FileObject a{}, b{};
  if (fstat(descriptor_, &held) != 0 || lstat(path_.c_str(), &named) != 0 ||
      !from_stat(held, a) || !from_stat(named, b) || !same_file(a, b) || !same_file(a, original_)) {
    failed_ = true;
    return false;
  }
  output = a;
  return true;
}
MacOSMappingSource::MacOSMappingSource() noexcept : calls_{::getpid, ::proc_pidinfo} {}
bool MacOSMappingSource::read(std::uintptr_t address, MappedFile& output) noexcept {
  output = {};
  if (address == 0 || !calls_.pid || !calls_.info) return false;
  const int pid = calls_.pid();
  if (pid <= 0) return false;
  proc_regionwithpathinfo r{};
  const auto size = static_cast<int>(sizeof(r));
  if (calls_.info(pid, PROC_PIDREGIONPATHINFO, address, &r, size) != size || calls_.pid() != pid) return false;
  const auto& s = r.prp_vip.vip_vi.vi_stat;
  if (!S_ISREG(s.vst_mode) || s.vst_size <= 0 || s.vst_mtimensec < 0 || s.vst_ctimensec < 0 ||
      s.vst_mtimensec >= 1000000000 || s.vst_ctimensec >= 1000000000) return false;
  FileObject f{s.vst_dev, s.vst_ino, static_cast<std::uint64_t>(s.vst_size),
    s.vst_mtime, s.vst_ctime, static_cast<std::uint32_t>(s.vst_mtimensec), static_cast<std::uint32_t>(s.vst_ctimensec)};
  if (!valid_file(f) || r.prp_prinfo.pri_address != address || r.prp_prinfo.pri_size == 0 ||
      r.prp_prinfo.pri_offset != 0 || r.prp_prinfo.pri_address > UINT64_MAX - r.prp_prinfo.pri_size) return false;
  output = {r.prp_prinfo.pri_address, r.prp_prinfo.pri_size, r.prp_prinfo.pri_offset, f};
  return true;
}
bool MacOSImageEvents::read(ImageSnapshot& output) noexcept {
  output = {};
  auto& events = registry();
  const int pid = getpid();
  int empty = 0;
  events.owner.compare_exchange_strong(empty, pid);
  if (pid <= 0 || events.owner.load() != pid || events.failed.load()) return false;
  if (pthread_once(&events.once, register_events) != 0 || pthread_mutex_lock(&events.mutex) != 0) {
    events.failed.store(true);
    return false;
  }
  const bool ok = events.ledger.read(output);
  if (pthread_mutex_unlock(&events.mutex) != 0) events.failed.store(true);
  if (!ok || events.failed.load()) { output = {}; return false; }
  return true;
}
} // namespace sh3::observer
