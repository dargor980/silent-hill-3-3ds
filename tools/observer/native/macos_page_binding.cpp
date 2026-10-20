#include "sh3_observer/macos_page_binding.hpp"
#include <fcntl.h>
#include <mach/mach.h>
#include <mach/mach_vm.h>
#include <mach/vm_statistics.h>
#include <sys/mman.h>
#include <sys/stat.h>
#include <unistd.h>
#include <cstring>
#include <limits>
#include <string_view>
#include <utility>

namespace sh3::observer {
namespace {
int open_file(const std::string& path) noexcept {
  if (path.empty() || path.front() != '/' || path.size() > 4096 || path.find('\0') != std::string::npos) return -1;
  int parent = open("/", O_RDONLY | O_DIRECTORY | O_CLOEXEC);
  if (parent < 0) return -1;
  for (std::size_t start = 1; start <= path.size();) {
    const auto slash = path.find('/', start);
    const bool last = slash == std::string::npos;
    const auto part = std::string_view(path).substr(start, last ? path.size() - start : slash - start);
    if (part.empty() || part == "." || part == ".." || part.size() > 255) { close(parent); return -1; }
    char component[256]{}; std::memcpy(component, part.data(), part.size());
    const auto next = openat(parent, component, O_RDONLY | O_CLOEXEC | O_NOFOLLOW | O_NONBLOCK | (last ? 0 : O_DIRECTORY));
    close(parent);
    if (next < 0 || last) return next;
    parent = next; start = slash + 1;
  }
  close(parent); return -1;
}
bool metadata(int fd, FileObject& out) noexcept {
  struct stat s{};
  if (fstat(fd, &s) != 0 || !S_ISREG(s.st_mode) || s.st_size <= 0 ||
      s.st_mtimespec.tv_nsec < 0 || s.st_ctimespec.tv_nsec < 0 ||
      s.st_mtimespec.tv_nsec >= 1000000000 || s.st_ctimespec.tv_nsec >= 1000000000) return false;
  out = {static_cast<std::uint32_t>(s.st_dev), s.st_ino, static_cast<std::uint64_t>(s.st_size),
    s.st_mtimespec.tv_sec, s.st_ctimespec.tv_sec, static_cast<std::uint32_t>(s.st_mtimespec.tv_nsec),
    static_cast<std::uint32_t>(s.st_ctimespec.tv_nsec)};
  return valid_file(out);
}
}
MacOSPageSource::MacOSPageSource() noexcept : MacOSPageSource({::getpid, ::mach_vm_read_overwrite, ::mach_vm_page_info}) {}
MacOSPageSource::MacOSPageSource(MacOSPageCalls calls) noexcept : calls_(calls), owner_(calls.pid ? calls.pid() : 0) {}
bool MacOSPageSource::read(std::uintptr_t address, PageReading& out) noexcept {
  out = {};
  if (address == 0 || !calls_.pid || !calls_.copy || !calls_.info || owner_ <= 0 || calls_.pid() != owner_) return false;
  unsigned char scratch{}; mach_vm_size_t copied{};
  if (calls_.copy(mach_task_self(), address, 1, reinterpret_cast<mach_vm_address_t>(&scratch), &copied) != KERN_SUCCESS || copied != 1) return false;
  vm_page_info_basic_data_t info{}; mach_msg_type_number_t count = VM_PAGE_INFO_BASIC_COUNT;
  if (calls_.info(mach_task_self(), address, VM_PAGE_INFO_BASIC,
      reinterpret_cast<vm_page_info_t>(&info), &count) != KERN_SUCCESS || count != VM_PAGE_INFO_BASIC_COUNT || calls_.pid() != owner_) return false;
  constexpr int rejected = VM_PAGE_QUERY_PAGE_DIRTY | VM_PAGE_QUERY_PAGE_COPIED |
    VM_PAGE_QUERY_PAGE_PAGED_OUT | VM_PAGE_QUERY_PAGE_FICTITIOUS | VM_PAGE_QUERY_PAGE_CS_TAINTED;
  out = {info.object_id, info.offset, (info.disposition & VM_PAGE_QUERY_PAGE_PRESENT) != 0,
    (info.disposition & VM_PAGE_QUERY_PAGE_EXTERNAL) != 0, (info.disposition & rejected) != 0};
  return true;
}
MacOSPageAnchor::MacOSPageAnchor(std::string path) noexcept : MacOSPageAnchor(std::move(path), ::pread) {}
MacOSPageAnchor::MacOSPageAnchor(std::string path, ReadAt reader) noexcept
  : path_(std::move(path)), owner_(getpid()), reader_(reader) {
  if (!reader_) return;
  descriptor_ = open_file(path_);
  if (descriptor_ < 0 || !metadata(descriptor_, original_)) return;
  auto mapped = mmap(nullptr, 1, PROT_READ, MAP_SHARED, descriptor_, 0);
  if (mapped == MAP_FAILED) return;
  mapping_ = mapped; failed_ = false;
}
MacOSPageAnchor::~MacOSPageAnchor() { (void)close(); }
bool MacOSPageAnchor::close() noexcept {
  failed_ = true;
  if (mapping_ && munmap(mapping_, 1) != 0) close_ok_ = false;
  mapping_ = nullptr;
  const int descriptor = descriptor_; descriptor_ = -1;
  if (descriptor >= 0 && ::close(descriptor) != 0) close_ok_ = false;
  return close_ok_;
}
bool MacOSPageAnchor::identity(FileObject& out) noexcept {
  FileObject held{}, named{};
  const auto fd = open_file(path_);
  if (fd < 0) return false;
  const bool ok = metadata(descriptor_, held) && metadata(fd, named) &&
    same_file(held, named) && same_file(held, original_);
  if (::close(fd) != 0) { close_ok_ = false; return false; }
  if (ok) out = held;
  return ok;
}
bool MacOSPageAnchor::read(PageFileReading& out) noexcept {
  out = {};
  if (failed_) return false;
  FileObject before{}, after{}; PageReading page{};
  if (owner_ <= 0 || getpid() != owner_ || !identity(before) ||
      !pages_.read(reinterpret_cast<std::uintptr_t>(mapping_), page) || !identity(after) || !same_file(before, after)) {
    failed_ = true; return false;
  }
  out = {before, page}; return true;
}
bool MacOSPageAnchor::read(FileObject& out) noexcept {
  out = {};
  if (failed_) return false;
  FileObject value{};
  if (owner_ <= 0 || getpid() != owner_ || !identity(value)) { failed_ = true; return false; }
  out = value; return true;
}
bool MacOSPageAnchor::read_at(std::uint64_t offset, void* bytes, std::size_t wanted, std::size_t& got) noexcept {
  got = 0;
  if (failed_) return false;
  if (owner_ <= 0 || getpid() != owner_ || !bytes || wanted == 0 || wanted > digest_block_size ||
      offset > original_.size || offset > static_cast<std::uint64_t>(std::numeric_limits<off_t>::max())) {
    failed_ = true; return false;
  }
  // The same retained descriptor supplies the reference mapping and every hash byte.
  const auto n = reader_(descriptor_, bytes, wanted, static_cast<off_t>(offset));
  if (n < 0 || static_cast<std::uint64_t>(n) > wanted || getpid() != owner_) { failed_ = true; return false; }
  got = static_cast<std::size_t>(n); return true;
}
} // namespace sh3::observer
