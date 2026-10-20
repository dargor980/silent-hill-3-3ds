#include "sh3_observer/inventory.hpp"
#include <algorithm>
#include <new>
#include <limits>
#include <string_view>

namespace sh3::observer {
namespace {
bool nonzero(const Sha256& hash) noexcept {
  return std::any_of(hash.begin(), hash.end(), [](auto b) { return b != 0; });
}
bool normalize(ImageSnapshot& images) noexcept {
  if (images.count == 0 || images.count > image_capacity || images.revision == 0 ||
      images.revision == std::numeric_limits<std::uint64_t>::max()) return false;
  auto end = images.addresses.begin() + images.count;
  std::sort(images.addresses.begin(), end);
  return images.addresses[0] != 0 && std::adjacent_find(images.addresses.begin(), end) == end;
}
bool same_images(const ImageSnapshot& a, const ImageSnapshot& b) noexcept {
  return a.revision == b.revision && a.count == b.count &&
    std::equal(a.addresses.begin(), a.addresses.begin() + a.count, b.addresses.begin());
}
bool valid_mapping(const MappedFile& m, std::uintptr_t address) noexcept {
  return m.address == address && m.size != 0 && m.offset == 0 &&
    m.size <= std::numeric_limits<std::uint64_t>::max() - m.address && valid_file(m.file);
}
bool same_mapping(const MappedFile& a, const MappedFile& b) noexcept {
  return a.address == b.address && a.size == b.size && a.offset == b.offset && same_file(a.file, b.file);
}
bool number(DigestEngine& hash, std::uint64_t value) noexcept {
  std::array<std::uint8_t, 8> bytes{};
  for (unsigned i = 0; i < 8; ++i) bytes[i] = static_cast<std::uint8_t>(value >> (8 * i));
  return hash.update(bytes.data(), bytes.size());
}
bool start(DigestEngine& hash, std::string_view domain, const Sha256& identity, std::uint64_t count) noexcept {
  return hash.begin() && hash.update(domain.data(), domain.size()) &&
    hash.update(identity.data(), identity.size()) && number(hash, count);
}
bool object(DigestEngine& hash, const FileObject& f) noexcept {
  return number(hash, f.device) && number(hash, f.inode) && number(hash, f.size) &&
    number(hash, static_cast<std::uint64_t>(f.modified_seconds)) &&
    number(hash, static_cast<std::uint64_t>(f.changed_seconds)) && number(hash, f.modified_ns) && number(hash, f.changed_ns);
}
}
struct InventoryGuard::Scratch {
  ImageSnapshot before{}, after{};
  std::array<MappedFile, image_capacity> mapped{};
  std::array<std::size_t, image_capacity> indices{};
};
InventoryGuard::~InventoryGuard() = default;
InventoryGuard::InventoryGuard(Sha256 evidence, ProcessBirth& birth, ManifestGuard& manifest,
  ImageSnapshotSource& images, MappingSource& mappings, DigestEngine& hash) noexcept
  : evidence_(evidence), birth_(birth), manifest_(manifest), images_(images), mappings_(mappings), hash_(hash) {
  if (!nonzero(evidence_)) failure_ = InventoryFailure::invalid;
  static_assert(sizeof(Scratch) <= 256 * 1024);
  static_assert(sizeof(InventoryGuard) <= 512);
  if (failure_ == InventoryFailure::none) {
    scratch_.reset(new (std::nothrow) Scratch);
    if (!scratch_) failure_ = InventoryFailure::storage;
  }
}
InventoryResult InventoryGuard::fail(InventoryFailure reason) noexcept {
  if (failure_ == InventoryFailure::none) failure_ = reason;
  baseline_ = {};
  InventoryResult result{}; result.failure = failure_; return result;
}
void InventoryGuard::lose() noexcept { (void)fail(InventoryFailure::lost); }
InventoryResult InventoryGuard::sample() noexcept {
  if (failure_ != InventoryFailure::none) return fail(failure_);
  const auto birth = birth_.sample();
  if (birth.failure != BirthFailure::none) return fail(InventoryFailure::birth);
  auto& before = scratch_->before; auto& after = scratch_->after;
  before = {}; after = {};
  if (!images_.read(before)) return fail(InventoryFailure::loader);
  if (!normalize(before)) return fail(InventoryFailure::invalid);
  const auto files = manifest_.sample();
  if (files.failure != ManifestFailure::none) return fail(InventoryFailure::manifest);
  for (std::size_t i = 0; i < files.count; ++i)
    for (std::size_t j = 0; j < i; ++j)
      if (files.files[i].object.device == files.files[j].object.device &&
          files.files[i].object.inode == files.files[j].object.inode) return fail(InventoryFailure::ambiguous);
  auto& mapped = scratch_->mapped;
  auto& indices = scratch_->indices;
  for (unsigned pass = 0; pass < 2; ++pass) {
    for (std::size_t i = 0; i < before.count; ++i) {
      MappedFile value{};
      if (!mappings_.read(before.addresses[i], value)) return fail(InventoryFailure::mapping);
      if (!valid_mapping(value, before.addresses[i])) return fail(InventoryFailure::invalid);
      std::size_t index = 0;
      while (index < files.count && !same_file(value.file, files.files[index].object)) ++index;
      if (index == files.count) return fail(InventoryFailure::uncovered);
      if (pass == 1 && !same_mapping(mapped[i], value)) return fail(InventoryFailure::changed);
      mapped[i] = value; indices[i] = index;
    }
  }
  const auto final_files = manifest_.sample();
  if (final_files.failure != ManifestFailure::none) return fail(InventoryFailure::manifest);
  // ManifestGuard itself enforces continuity; compare again at this boundary.
  if (files.count != final_files.count) return fail(InventoryFailure::changed);
  for (std::size_t i = 0; i < files.count; ++i)
    if (!same_file(files.files[i].object, final_files.files[i].object) ||
        files.files[i].sha256 != final_files.files[i].sha256) return fail(InventoryFailure::changed);
  InventoryResult result{};
  if (!start(hash_, "SH3:file-objects:v1", evidence_, files.count)) return fail(InventoryFailure::digest);
  for (std::size_t i = 0; i < files.count; ++i) {
    const auto& file = files.files[i];
    if (!number(hash_, i) || !object(hash_, file.object) || !hash_.update(file.sha256.data(), file.sha256.size()))
      return fail(InventoryFailure::digest);
  }
  if (!hash_.finish(result.file_objects) || !nonzero(result.file_objects)) return fail(InventoryFailure::digest);
  if (!start(hash_, "SH3:loaded-images:v1", result.file_objects, before.revision) || !number(hash_, before.count))
    return fail(InventoryFailure::digest);
  for (std::size_t i = 0; i < before.count; ++i)
    if (!number(hash_, mapped[i].address) || !number(hash_, mapped[i].size) ||
        !number(hash_, mapped[i].offset) || !number(hash_, indices[i])) return fail(InventoryFailure::digest);
  if (!hash_.finish(result.loaded_images) || !nonzero(result.loaded_images)) return fail(InventoryFailure::digest);
  if (!images_.read(after)) return fail(InventoryFailure::loader);
  if (!normalize(after)) return fail(InventoryFailure::invalid);
  if (!same_images(before, after)) return fail(InventoryFailure::changed);
  const auto final_birth = birth_.sample();
  if (final_birth.failure != BirthFailure::none) return fail(InventoryFailure::birth);
  if (!same_process_key(birth.key, final_birth.key)) return fail(InventoryFailure::changed);
  result.process = birth.key; result.loader_revision = before.revision; result.image_count = before.count;
  if (ready_ && (!same_process_key(result.process, baseline_.process) ||
      result.file_objects != baseline_.file_objects || result.loaded_images != baseline_.loaded_images ||
      result.loader_revision != baseline_.loader_revision || result.image_count != baseline_.image_count))
    return fail(InventoryFailure::changed);
  baseline_ = result; ready_ = true; return result;
}
} // namespace sh3::observer
