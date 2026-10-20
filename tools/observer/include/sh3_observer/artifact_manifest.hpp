#pragma once
#include "sh3_observer/image_identity.hpp"
#include <string>
#include <string_view>
#include <vector>

namespace sh3::observer {
using Sha256 = std::array<std::uint8_t, 32>;
inline constexpr std::size_t artifact_file_capacity = 256;
inline constexpr std::uint64_t artifact_file_limit = 256ULL * 1024 * 1024;
inline constexpr std::uint64_t artifact_total_limit = 512ULL * 1024 * 1024;
// Host policy selected by the trusted provider, never by a client request.
enum class ArtifactDomain { bundle, system_cache };
inline constexpr std::uint64_t cache_file_limit = 2ULL * 1024 * 1024 * 1024;
inline constexpr std::uint64_t cache_total_limit = 16ULL * 1024 * 1024 * 1024;
inline constexpr std::size_t cache_file_capacity = 32;
inline constexpr std::size_t digest_block_size = 65536;
struct FileDigest { FileObject object{}; Sha256 sha256{}; };
class ByteSource {
public:
  virtual ~ByteSource() = default;
  virtual bool read_at(std::uint64_t, void*, std::size_t requested, std::size_t& received) noexcept = 0;
};
class DigestEngine {
public:
  virtual ~DigestEngine() = default;
  virtual bool begin() noexcept = 0;
  virtual bool update(const void*, std::size_t) noexcept = 0;
  virtual bool finish(Sha256&) noexcept = 0;
};
enum class ManifestFailure { none, invalid, unavailable, mismatch, changed, lost };
class AnchoredDigest final {
public:
  AnchoredDigest(FileIdentitySource& identity, ByteSource& bytes, DigestEngine& hash,
                 ArtifactDomain domain = ArtifactDomain::bundle) noexcept
    : identity_(identity), bytes_(bytes), hash_(hash), domain_(domain) {}
  AnchoredDigest(const AnchoredDigest&) = delete;
  AnchoredDigest& operator=(const AnchoredDigest&) = delete;
  ManifestFailure sample(FileDigest&) noexcept;
  void lose() noexcept;
private:
  ManifestFailure fail(ManifestFailure) noexcept;
  FileIdentitySource& identity_;
  ByteSource& bytes_;
  DigestEngine& hash_;
  const ArtifactDomain domain_;
  FileDigest baseline_{};
  ManifestFailure failure_{ManifestFailure::none};
  bool ready_{};
};
struct ExpectedFile { std::string name; std::uint64_t size{}; Sha256 sha256{}; };
bool valid_artifact_name(std::string_view) noexcept;
bool valid_manifest(const std::vector<ExpectedFile>&, ArtifactDomain = ArtifactDomain::bundle) noexcept;
class ArtifactSource {
public:
  virtual ~ArtifactSource() = default;
  virtual bool read(std::string_view, FileDigest&) noexcept = 0;
};
struct ManifestResult {
  std::array<FileDigest, artifact_file_capacity> files{};
  std::size_t count{};
  ManifestFailure failure{ManifestFailure::none};
};
class ManifestGuard final {
public:
  // Trusted launcher configuration, copied/owned before any observation.
  ManifestGuard(std::vector<ExpectedFile>, ArtifactSource&, ArtifactDomain = ArtifactDomain::bundle);
  ManifestGuard(const ManifestGuard&) = delete;
  ManifestGuard& operator=(const ManifestGuard&) = delete;
  ManifestResult sample() noexcept;
  void lose() noexcept;
private:
  ManifestResult fail(ManifestFailure) noexcept;
  const std::vector<ExpectedFile> expected_;
  ArtifactSource& source_;
  std::array<FileDigest, artifact_file_capacity> baseline_{};
  ManifestFailure failure_{ManifestFailure::none};
  bool ready_{};
};
} // namespace sh3::observer
