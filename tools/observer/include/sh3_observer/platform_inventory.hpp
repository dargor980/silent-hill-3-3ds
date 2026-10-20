#pragma once
#include <memory>
#include "sh3_observer/inventory.hpp"
#include "sh3_observer/macho_slice.hpp"

namespace sh3::observer {
using CacheUuid = std::array<std::uint8_t, 16>;
enum class IdentityProfile : std::uint8_t { unknown, macos_platform_v1, macos_platform_slices_v2 };
struct PlatformPolicy {
  IdentityProfile profile{IdentityProfile::unknown};
  Sha256 policy_evidence{}, application_evidence{}, platform_evidence{};
  CacheUuid expected_cache{};
  std::uintptr_t main_image{};
  std::size_t main_file{};
};
enum class ImageOriginKind : std::uint8_t { unknown, application, platform_cache };
struct CacheImage {
  std::uint64_t address{}, base{}, size{};
  CacheUuid uuid{};
};
struct ImageOrigin {
  ImageOriginKind kind{ImageOriginKind::unknown};
  MappedFile application{};
  CacheImage cache{};
  MachSlice slice{};
};
// Trusted provider port: cache membership must identify the exact loaded header.
// A path, tag, Mach-O flag, address range or UUID alone is not a membership proof.
class ImageOriginSource {
public:
  virtual ~ImageOriginSource() = default;
  virtual bool read(std::uintptr_t, ImageOrigin&) noexcept = 0;
};
enum class PlatformInventoryFailure : std::uint8_t {
  none, policy, birth, loader, manifest, origin, invalid, uncovered, ambiguous,
  main_image, changed, digest, lost, storage
};
enum class IdentityScope : std::uint8_t { unknown, application_headers };
struct PlatformInventoryResult {
  IdentityProfile profile{IdentityProfile::unknown};
  IdentityScope scope{IdentityScope::unknown};
  bool platform_assumed{};
  ProcessKey process{};
  Sha256 file_objects{}, classified_images{};
  Sha256 policy_evidence{}, application_evidence{}, platform_evidence{};
  std::uint64_t loader_revision{};
  std::size_t application_images{}, platform_images{};
  PlatformInventoryFailure failure{PlatformInventoryFailure::none};
};
// Deliberately distinct from strict InventoryGuard/InventoryResult. No admission.
class PlatformInventoryGuard final {
public:
  PlatformInventoryGuard(PlatformPolicy, ProcessBirth&, ManifestGuard&,
                         ImageSnapshotSource&, ImageOriginSource&, DigestEngine&) noexcept;
  ~PlatformInventoryGuard();
  PlatformInventoryGuard(const PlatformInventoryGuard&) = delete;
  PlatformInventoryGuard& operator=(const PlatformInventoryGuard&) = delete;
  PlatformInventoryResult sample() noexcept;
  void lose() noexcept;
private:
  struct Scratch;
  std::unique_ptr<Scratch> scratch_;
  PlatformInventoryResult fail(PlatformInventoryFailure) noexcept;
  const PlatformPolicy policy_;
  ProcessBirth& birth_;
  ManifestGuard& manifest_;
  ImageSnapshotSource& images_;
  ImageOriginSource& origins_;
  DigestEngine& hash_;
  PlatformInventoryResult baseline_{};
  PlatformInventoryFailure failure_{PlatformInventoryFailure::none};
  bool ready_{};
};
} // namespace sh3::observer
