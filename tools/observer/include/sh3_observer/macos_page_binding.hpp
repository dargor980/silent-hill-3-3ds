#pragma once
#include "sh3_observer/page_binding.hpp"
#include "sh3_observer/artifact_manifest.hpp"
#include <string>
#include <sys/types.h>
#include <mach/mach_vm.h>

namespace sh3::observer {
// Internal fault seams, never selected through client transport.
struct MacOSPageCalls {
  int (*pid)();
  decltype(&::mach_vm_read_overwrite) copy;
  decltype(&::mach_vm_page_info) info;
};
class MacOSPageSource final : public PageSource {
public:
  MacOSPageSource() noexcept;
  explicit MacOSPageSource(MacOSPageCalls) noexcept;
  bool read(std::uintptr_t, PageReading&) noexcept override;
private:
  MacOSPageCalls calls_;
  int owner_;
};
class MacOSPageAnchor final : public PageFileSource, public FileIdentitySource, public ByteSource {
public:
  using ReadAt = ssize_t (*)(int, void*, std::size_t, off_t);
  explicit MacOSPageAnchor(std::string path) noexcept;
  MacOSPageAnchor(std::string path, ReadAt) noexcept;
  ~MacOSPageAnchor() override;
  bool close() noexcept;
  MacOSPageAnchor(const MacOSPageAnchor&) = delete;
  MacOSPageAnchor& operator=(const MacOSPageAnchor&) = delete;
  bool read(PageFileReading&) noexcept override;
  bool read(FileObject&) noexcept override;
  bool read_at(std::uint64_t, void*, std::size_t, std::size_t&) noexcept override;
private:
  bool identity(FileObject&) noexcept;
  std::string path_;
  int owner_, descriptor_{-1};
  void* mapping_{};
  FileObject original_{};
  MacOSPageSource pages_;
  ReadAt reader_;
  bool failed_{true};
  bool close_ok_{true};
};
} // namespace sh3::observer
