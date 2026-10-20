#pragma once
#include "sh3_observer/platform_inventory.hpp"

namespace sh3::observer {
inline constexpr std::size_t launch_manifest_limit = 1024 * 1024;
inline constexpr std::size_t launch_root_capacity = 8;
struct LaunchFile { std::size_t root{}; ExpectedFile file; };
struct LaunchManifest {
  std::vector<std::string> roots;
  std::vector<LaunchFile> files;
  std::size_t main_file{};
  CacheUuid cache{};
  Sha256 policy_evidence{}, platform_evidence{};
};
enum class LaunchFailure { none, invalid, unavailable, identity, digest, malformed };
bool valid_launch_manifest(const LaunchManifest&) noexcept;
std::vector<ExpectedFile> launch_expected_files(const LaunchManifest&);
// Pure decoding does not establish trust; use the reader with a launcher-pinned hash.
LaunchFailure decode_launch_manifest(const std::uint8_t*, std::size_t, LaunchManifest&);
LaunchFailure read_launch_manifest(FileIdentitySource&, ByteSource&, DigestEngine&,
                                  const Sha256& expected, LaunchManifest&);
} // namespace sh3::observer
