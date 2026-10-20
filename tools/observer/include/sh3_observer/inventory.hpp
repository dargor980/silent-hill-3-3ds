#pragma once
#include <memory>
#include "sh3_observer/artifact_manifest.hpp"
#include "sh3_observer/process_birth.hpp"

namespace sh3::observer {
class ImageSnapshotSource {
public:
  virtual ~ImageSnapshotSource() = default;
  virtual bool read(ImageSnapshot&) noexcept = 0;
};
enum class InventoryFailure { none, invalid, birth, loader, manifest, mapping, uncovered, ambiguous, changed, digest, lost, storage };
struct InventoryResult {
  ProcessKey process{};
  Sha256 file_objects{}, loaded_images{};
  std::uint64_t loader_revision{};
  std::size_t image_count{};
  InventoryFailure failure{InventoryFailure::none};
};
// Single owner; expected evidence identity is trusted launcher configuration.
// Covers NI header regions. Does not grant admission or capture capabilities.
class InventoryGuard final {
public:
  InventoryGuard(Sha256 manifest_evidence, ProcessBirth&, ManifestGuard&,
                 ImageSnapshotSource&, MappingSource&, DigestEngine&) noexcept;
  ~InventoryGuard();
  InventoryGuard(const InventoryGuard&) = delete;
  InventoryGuard& operator=(const InventoryGuard&) = delete;
  InventoryResult sample() noexcept;
  void lose() noexcept;
private:
  struct Scratch;
  std::unique_ptr<Scratch> scratch_;
  InventoryResult fail(InventoryFailure) noexcept;
  Sha256 evidence_;
  ProcessBirth& birth_;
  ManifestGuard& manifest_;
  ImageSnapshotSource& images_;
  MappingSource& mappings_;
  DigestEngine& hash_;
  InventoryResult baseline_{};
  InventoryFailure failure_{InventoryFailure::none};
  bool ready_{};
};
} // namespace sh3::observer
