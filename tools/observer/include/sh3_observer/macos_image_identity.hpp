#pragma once
#include "sh3_observer/image_identity.hpp"
#include <string>

namespace sh3::observer {
class MacOSFileAnchor final : public FileIdentitySource {
public:
  explicit MacOSFileAnchor(std::string path) noexcept;
  ~MacOSFileAnchor() override;
  MacOSFileAnchor(const MacOSFileAnchor&) = delete;
  MacOSFileAnchor& operator=(const MacOSFileAnchor&) = delete;
  bool read(FileObject&) noexcept override;
private:
  std::string path_;
  int descriptor_{-1};
  FileObject original_{};
  bool failed_{true};
};
struct MacOSMappingCalls {
  int (*pid)();
  int (*info)(int, int, std::uint64_t, void*, int);
};
class MacOSMappingSource final : public MappingSource {
public:
  MacOSMappingSource() noexcept;
  explicit MacOSMappingSource(MacOSMappingCalls calls) noexcept : calls_(calls) {}
  bool read(std::uintptr_t, MappedFile&) noexcept override;
private:
  MacOSMappingCalls calls_;
};
class MacOSImageEvents final {
public:
  // Process-lifetime registration. Call before starting provider worker threads.
  // A forked child cannot reuse this registry; it must exec a fresh process.
  static bool read(ImageSnapshot&) noexcept;
};
} // namespace sh3::observer
