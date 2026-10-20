#pragma once
#include "sh3_observer/artifact_manifest.hpp"
#include "sh3_observer/inspection_control.hpp"
#include <CommonCrypto/CommonDigest.h>
#include <memory>
#include <sys/types.h>

namespace sh3::observer {
class MacOSSha256 final : public DigestEngine {
public:
  explicit MacOSSha256(InspectionControl* control = nullptr) noexcept : control_(control) {}
  bool begin() noexcept override;
  bool update(const void*, std::size_t) noexcept override;
  bool finish(Sha256&) noexcept override;
private:
  bool allowed() noexcept;
  InspectionControl* control_;
  bool stopped_{};
  CC_SHA256_CTX context_{};
  bool active_{};
};
class MacOSArtifactFiles final : public ArtifactSource {
public:
  using ReadAt = ssize_t (*)(int, void*, std::size_t, off_t);
  MacOSArtifactFiles(std::string absolute_root, const std::vector<ExpectedFile>&);
  // Internal fault-injection seam, not selected by a client/transport.
  MacOSArtifactFiles(std::string absolute_root, const std::vector<ExpectedFile>&, ReadAt);
  MacOSArtifactFiles(std::string absolute_root, const std::vector<ExpectedFile>&, InspectionControl&);
  MacOSArtifactFiles(std::string absolute_root, const std::vector<ExpectedFile>&, ReadAt, InspectionControl*);
  ~MacOSArtifactFiles() override;
  MacOSArtifactFiles(const MacOSArtifactFiles&) = delete;
  MacOSArtifactFiles& operator=(const MacOSArtifactFiles&) = delete;
  bool read(std::string_view, FileDigest&) noexcept override;
  bool close() noexcept;
private:
  struct Impl;
  std::unique_ptr<Impl> impl_;
};
} // namespace sh3::observer
