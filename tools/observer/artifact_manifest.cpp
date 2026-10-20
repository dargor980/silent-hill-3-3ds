#include "sh3_observer/artifact_manifest.hpp"
#include <algorithm>
#include <utility>

namespace sh3::observer {
namespace {
std::uint64_t file_limit(ArtifactDomain domain) noexcept {
  switch (domain) {
    case ArtifactDomain::bundle: return artifact_file_limit;
    case ArtifactDomain::system_cache: return cache_file_limit;
  }
  return 0;
}
bool nonzero(const Sha256& value) noexcept {
  return std::any_of(value.begin(), value.end(), [](auto byte) { return byte != 0; });
}
bool equal(const FileDigest& a, const FileDigest& b) noexcept {
  return same_file(a.object, b.object) && a.sha256 == b.sha256;
}
}
ManifestFailure AnchoredDigest::fail(ManifestFailure reason) noexcept {
  if (failure_ == ManifestFailure::none) failure_ = reason;
  baseline_ = {};
  return failure_;
}
void AnchoredDigest::lose() noexcept { (void)fail(ManifestFailure::lost); }
ManifestFailure AnchoredDigest::sample(FileDigest& out) noexcept {
  out = {};
  if (failure_ != ManifestFailure::none) return failure_;
  FileObject before{}, after{};
  if (!identity_.read(before)) return fail(ManifestFailure::unavailable);
  if (!valid_file(before) || before.size > file_limit(domain_)) return fail(ManifestFailure::invalid);
  if (ready_ && !same_file(before, baseline_.object)) return fail(ManifestFailure::changed);
  if (!hash_.begin()) return fail(ManifestFailure::unavailable);
  std::array<std::uint8_t, digest_block_size> buffer{};
  for (std::uint64_t offset = 0; offset < before.size;) {
    const auto wanted = static_cast<std::size_t>(std::min<std::uint64_t>(buffer.size(), before.size - offset));
    std::size_t got{};
    if (!bytes_.read_at(offset, buffer.data(), wanted, got) || got != wanted || !hash_.update(buffer.data(), got))
      return fail(ManifestFailure::unavailable);
    offset += got;
  }
  std::size_t trailing{};
  Sha256 digest{};
  if (!bytes_.read_at(before.size, buffer.data(), 1, trailing) || trailing != 0 ||
      !hash_.finish(digest) || !identity_.read(after)) return fail(ManifestFailure::unavailable);
  if (!nonzero(digest) || !valid_file(after)) return fail(ManifestFailure::invalid);
  if (!same_file(before, after) || (ready_ && baseline_.sha256 != digest)) return fail(ManifestFailure::changed);
  baseline_ = {before, digest};
  ready_ = true;
  out = baseline_;
  return ManifestFailure::none;
}
bool valid_artifact_name(std::string_view name) noexcept {
  if (name.empty() || name.size() > 1024) return false;
  std::size_t start = 0;
  for (std::size_t i = 0; i <= name.size(); ++i) {
    if (i == name.size() || name[i] == '/') {
      const auto part = name.substr(start, i - start);
      if (part.empty() || part.size() > 255 || part == "." || part == "..") return false;
      start = i + 1;
    } else {
      const auto c = static_cast<unsigned char>(name[i]);
      if (c < 32 || c > 126 || c == '\\' || c == ':') return false;
    }
  }
  return true;
}
bool valid_manifest(const std::vector<ExpectedFile>& files, ArtifactDomain domain) noexcept {
  const auto limit = file_limit(domain);
  const auto total_limit = domain == ArtifactDomain::bundle ? artifact_total_limit : cache_total_limit;
  const auto capacity = domain == ArtifactDomain::bundle ? artifact_file_capacity : cache_file_capacity;
  if (limit == 0 || files.empty() || files.size() > capacity) return false;
  std::uint64_t total = 0;
  std::string_view previous;
  for (const auto& file : files) {
    if (!valid_artifact_name(file.name) || file.name <= previous || file.size == 0 ||
        file.size > limit || !nonzero(file.sha256) || file.size > total_limit - total) return false;
    total += file.size;
    previous = file.name;
  }
  return true;
}
ManifestGuard::ManifestGuard(std::vector<ExpectedFile> files, ArtifactSource& source, ArtifactDomain domain)
  : expected_(std::move(files)), source_(source) {
  if (!valid_manifest(expected_, domain)) failure_ = ManifestFailure::invalid;
}
ManifestResult ManifestGuard::fail(ManifestFailure reason) noexcept {
  if (failure_ == ManifestFailure::none) failure_ = reason;
  baseline_ = {};
  return {{}, 0, failure_};
}
void ManifestGuard::lose() noexcept { (void)fail(ManifestFailure::lost); }
ManifestResult ManifestGuard::sample() noexcept {
  if (failure_ != ManifestFailure::none) return {{}, 0, failure_};
  ManifestResult result{};
  for (unsigned pass = 0; pass < 2; ++pass) {
    for (std::size_t i = 0; i < expected_.size(); ++i) {
      const auto& wanted = expected_[i];
      FileDigest value{};
      if (!source_.read(wanted.name, value)) return fail(ManifestFailure::unavailable);
      if (!valid_file(value.object) || !nonzero(value.sha256)) return fail(ManifestFailure::invalid);
      if (value.object.size != wanted.size || value.sha256 != wanted.sha256) return fail(ManifestFailure::mismatch);
      if ((ready_ && !equal(baseline_[i], value)) || (pass == 1 && !equal(result.files[i], value)))
        return fail(ManifestFailure::changed);
      result.files[i] = value;
    }
  }
  result.count = expected_.size();
  baseline_ = result.files;
  ready_ = true;
  return result;
}
} // namespace sh3::observer
