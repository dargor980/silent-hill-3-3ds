#include "sh3_observer/platform_inventory.hpp"
#include <algorithm>
#include <new>
#include <string_view>

namespace sh3::observer {
namespace {
template<std::size_t N> bool nonzero(const std::array<std::uint8_t,N>& bytes) noexcept {
  return std::any_of(bytes.begin(),bytes.end(),[](auto b){return b != 0;});
}
bool normalize(ImageSnapshot& images) noexcept {
  if (!images.count || images.count > image_capacity || !images.revision || images.revision == UINT64_MAX) return false;
  auto end = images.addresses.begin()+images.count;
  std::sort(images.addresses.begin(),end);
  return images.addresses[0] && std::adjacent_find(images.addresses.begin(),end) == end;
}
bool same_mapping(const MappedFile& a, const MappedFile& b) noexcept {
  return a.address == b.address && a.size == b.size && a.offset == b.offset && same_file(a.file,b.file);
}
bool same_cache(const CacheImage& a, const CacheImage& b) noexcept {
  return a.base == b.base && a.size == b.size && a.uuid == b.uuid;
}
bool same_origin(const ImageOrigin& a, const ImageOrigin& b) noexcept {
  return a.kind == b.kind && same_mapping(a.application,b.application) &&
    a.cache.address == b.cache.address && same_cache(a.cache,b.cache) && same_slice(a.slice,b.slice);
}
bool valid_origin(const ImageOrigin& o, std::uintptr_t address, const CacheUuid& uuid, IdentityProfile profile) noexcept {
  if (o.kind == ImageOriginKind::application) {
    const auto& m = o.application;
    return m.address == address && m.size && m.size <= UINT64_MAX-m.address && valid_file(m.file) &&
      !o.cache.address && same_cache(o.cache,{}) &&
      (profile == IdentityProfile::macos_platform_v1 ? !m.offset && same_slice(o.slice,{}) : valid_slice_binding({m,o.slice}));
  }
  if (o.kind == ImageOriginKind::platform_cache) {
    const auto& c = o.cache;
    return c.address == address && c.base && c.size && c.size <= UINT64_MAX-c.base &&
      c.base <= address && address-c.base < c.size && c.uuid == uuid && same_mapping(o.application,{}) && same_slice(o.slice,{});
  }
  return false;
}
bool number(DigestEngine& h, std::uint64_t n) noexcept {
  std::array<std::uint8_t,8> bytes{};
  for (unsigned i=0;i<8;++i) bytes[i]=static_cast<std::uint8_t>(n>>(8*i));
  return h.update(bytes.data(),bytes.size());
}
bool domain(DigestEngine& h, std::string_view text) noexcept { return h.begin() && h.update(text.data(),text.size()); }
template<std::size_t N> bool bytes(DigestEngine& h, const std::array<std::uint8_t,N>& data) noexcept {
  return h.update(data.data(),data.size());
}
bool object(DigestEngine& h, const FileObject& f) noexcept {
  return number(h,f.device) && number(h,f.inode) && number(h,f.size) &&
    number(h,static_cast<std::uint64_t>(f.modified_seconds)) && number(h,static_cast<std::uint64_t>(f.changed_seconds)) &&
    number(h,f.modified_ns) && number(h,f.changed_ns);
}
}
struct PlatformInventoryGuard::Scratch {
  ImageSnapshot first{}, last{};
  std::array<ImageOrigin, image_capacity> observed{};
  std::array<std::size_t, image_capacity> indices{};
};
PlatformInventoryGuard::~PlatformInventoryGuard() = default;
PlatformInventoryGuard::PlatformInventoryGuard(PlatformPolicy policy, ProcessBirth& birth, ManifestGuard& manifest,
    ImageSnapshotSource& images, ImageOriginSource& origins, DigestEngine& hash) noexcept
  : policy_(policy), birth_(birth), manifest_(manifest), images_(images), origins_(origins), hash_(hash) {
  if ((policy_.profile != IdentityProfile::macos_platform_v1 && policy_.profile != IdentityProfile::macos_platform_slices_v2) || !nonzero(policy_.policy_evidence) ||
      !nonzero(policy_.application_evidence) || !nonzero(policy_.platform_evidence) ||
      !nonzero(policy_.expected_cache) || !policy_.main_image || policy_.main_file >= artifact_file_capacity)
    failure_ = PlatformInventoryFailure::policy;
  static_assert(sizeof(Scratch) <= 512 * 1024);
  static_assert(sizeof(PlatformInventoryGuard) <= 512);
  if (failure_ == PlatformInventoryFailure::none) {
    scratch_.reset(new (std::nothrow) Scratch);
    if (!scratch_) failure_ = PlatformInventoryFailure::storage;
  }
}
PlatformInventoryResult PlatformInventoryGuard::fail(PlatformInventoryFailure why) noexcept {
  if (failure_ == PlatformInventoryFailure::none) failure_ = why;
  baseline_ = {};
  PlatformInventoryResult result{}; result.failure = failure_; return result;
}
void PlatformInventoryGuard::lose() noexcept { (void)fail(PlatformInventoryFailure::lost); }
PlatformInventoryResult PlatformInventoryGuard::sample() noexcept {
  using Failure = PlatformInventoryFailure;
  if (failure_ != Failure::none) return fail(failure_);
  const auto birth = birth_.sample();
  if (birth.failure != BirthFailure::none) return fail(Failure::birth);
  auto& first = scratch_->first; auto& last = scratch_->last;
  first = {}; last = {};
  if (!images_.read(first)) return fail(Failure::loader);
  if (!normalize(first)) return fail(Failure::invalid);
  if (!std::binary_search(first.addresses.begin(),first.addresses.begin()+first.count,policy_.main_image)) return fail(Failure::main_image);
  const auto files = manifest_.sample();
  if (files.failure != ManifestFailure::none) return fail(Failure::manifest);
  if (policy_.main_file >= files.count) return fail(Failure::policy);
  std::uint64_t total{};
  for (std::size_t i=0;i<files.count;++i) {
    const auto size = files.files[i].object.size;
    if (size > artifact_file_limit || size > artifact_total_limit-total) return fail(Failure::policy);
    total += size;
    for (std::size_t j=0;j<i;++j)
      if (files.files[i].object.device == files.files[j].object.device && files.files[i].object.inode == files.files[j].object.inode)
        return fail(Failure::ambiguous);
  }
  auto& observed = scratch_->observed;
  auto& indices = scratch_->indices;
  CacheImage cache{}; bool cache_seen{};
  PlatformInventoryResult result{};
  for (unsigned pass=0;pass<2;++pass) {
    for (std::size_t i=0;i<first.count;++i) {
      ImageOrigin origin{};
      if (!origins_.read(first.addresses[i],origin)) return fail(Failure::origin);
      if (origin.kind == ImageOriginKind::unknown) return fail(Failure::uncovered);
      if (!valid_origin(origin,first.addresses[i],policy_.expected_cache,policy_.profile)) return fail(Failure::invalid);
      if (pass && !same_origin(observed[i],origin)) return fail(Failure::changed);
      if (origin.kind == ImageOriginKind::application) {
        std::size_t index{};
        while (index < files.count && !same_file(origin.application.file,files.files[index].object)) ++index;
        if (index == files.count) return fail(Failure::uncovered);
        if (first.addresses[i] == policy_.main_image && index != policy_.main_file) return fail(Failure::main_image);
        indices[i] = index;
        if (!pass) ++result.application_images;
      } else {
        if (first.addresses[i] == policy_.main_image) return fail(Failure::main_image);
        if (cache_seen && !same_cache(cache,origin.cache)) return fail(Failure::changed);
        cache = origin.cache; cache_seen = true;
        if (!pass) ++result.platform_images;
      }
      observed[i] = origin;
    }
  }
  const auto after_files = manifest_.sample();
  if (after_files.failure != ManifestFailure::none) return fail(Failure::manifest);
  if (files.count != after_files.count) return fail(Failure::changed);
  for (std::size_t i=0;i<files.count;++i)
    if (!same_file(files.files[i].object,after_files.files[i].object) || files.files[i].sha256 != after_files.files[i].sha256)
      return fail(Failure::changed);
  const bool slices = policy_.profile == IdentityProfile::macos_platform_slices_v2;
  if (!domain(hash_,slices ? "SH3:platform-files:v2" : "SH3:platform-files:v1") || !number(hash_,static_cast<std::uint8_t>(policy_.profile)) ||
      !bytes(hash_,policy_.policy_evidence) || !bytes(hash_,policy_.application_evidence) || !bytes(hash_,policy_.platform_evidence) ||
      !bytes(hash_,policy_.expected_cache) || !number(hash_,policy_.main_image) || !number(hash_,policy_.main_file) ||
      !number(hash_,files.count)) return fail(Failure::digest);
  for (std::size_t i=0;i<files.count;++i)
    if (!number(hash_,i) || !object(hash_,files.files[i].object) || !bytes(hash_,files.files[i].sha256)) return fail(Failure::digest);
  if (!hash_.finish(result.file_objects) || !nonzero(result.file_objects)) return fail(Failure::digest);
  if (!domain(hash_,slices ? "SH3:platform-images:v2" : "SH3:platform-images:v1") || !bytes(hash_,result.file_objects) ||
      !number(hash_,first.revision) || !number(hash_,first.count)) return fail(Failure::digest);
  for (std::size_t i=0;i<first.count;++i) {
    const auto& o = observed[i];
    if (!number(hash_,static_cast<std::uint8_t>(o.kind)) || !number(hash_,first.addresses[i])) return fail(Failure::digest);
    if (o.kind == ImageOriginKind::application) {
      if (!number(hash_,o.application.size) || !number(hash_,o.application.offset) || !number(hash_,indices[i])) return fail(Failure::digest);
      if (slices && (!number(hash_,static_cast<std::uint8_t>(o.slice.format)) || !number(hash_,o.slice.offset) ||
          !number(hash_,o.slice.size) || !bytes(hash_,o.slice.header))) return fail(Failure::digest);
    } else if (!number(hash_,o.cache.base) || !number(hash_,o.cache.size) || !bytes(hash_,o.cache.uuid)) return fail(Failure::digest);
  }
  if (!hash_.finish(result.classified_images) || !nonzero(result.classified_images)) return fail(Failure::digest);
  if (!images_.read(last)) return fail(Failure::loader);
  if (!normalize(last)) return fail(Failure::invalid);
  if (first.revision != last.revision || first.count != last.count ||
      !std::equal(first.addresses.begin(),first.addresses.begin()+first.count,last.addresses.begin())) return fail(Failure::changed);
  const auto end = birth_.sample();
  if (end.failure != BirthFailure::none) return fail(Failure::birth);
  if (!same_process_key(birth.key,end.key)) return fail(Failure::changed);
  result.profile = policy_.profile; result.scope = IdentityScope::application_headers; result.platform_assumed = true;
  result.process = birth.key; result.loader_revision = first.revision;
  result.policy_evidence = policy_.policy_evidence; result.application_evidence = policy_.application_evidence;
  result.platform_evidence = policy_.platform_evidence;
  if (ready_ && (!same_process_key(result.process,baseline_.process) || result.file_objects != baseline_.file_objects ||
      result.classified_images != baseline_.classified_images || result.loader_revision != baseline_.loader_revision ||
      result.application_images != baseline_.application_images || result.platform_images != baseline_.platform_images)) return fail(Failure::changed);
  baseline_ = result; ready_ = true; return result;
}
} // namespace sh3::observer
