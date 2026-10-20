#include "sh3_observer/macos_platform_origin.hpp"
#include "sh3_observer/macos_image_identity.hpp"
#include <algorithm>
#include <cstring>
#include <dlfcn.h>
#include <mach/mach.h>
#include <mach/mach_vm.h>
#include <mach-o/loader.h>
#include <unistd.h>

namespace sh3::observer {
namespace {
template<class T> T symbol(const char* name) noexcept { return reinterpret_cast<T>(dlsym(RTLD_DEFAULT,name)); }
bool normalize(ImageSnapshot& s) noexcept {
  if (!s.count || s.count > image_capacity || !s.revision || s.revision == UINT64_MAX) return false;
  const auto end = s.addresses.begin()+s.count;
  std::sort(s.addresses.begin(),end);
  return s.addresses[0] && std::adjacent_find(s.addresses.begin(),end) == end;
}
bool preflight() noexcept {
  const auto range = symbol<const void*(*)(std::size_t*)>("_dyld_get_shared_cache_range");
  if (!range) return false;
  std::size_t length{}; const auto base = reinterpret_cast<std::uintptr_t>(range(&length));
  if (!base || !length || length > UINT64_MAX-base) return false;
  ImageSnapshot first{}, last{};
  if (!MacOSImageEvents::read(first) || !normalize(first)) return false;
  for (std::size_t i=0;i<first.count;++i) {
    mach_header_64 header{}; mach_vm_size_t got{}; const auto address = first.addresses[i];
    if (mach_vm_read_overwrite(mach_task_self(),address,sizeof(header),reinterpret_cast<mach_vm_address_t>(&header),&got) != KERN_SUCCESS ||
        got != sizeof(header) || header.magic != MH_MAGIC_64) return false;
    // A rejection precondition, never a positive membership decision. The SPI
    // can abort on a forged cache bit outside its cache, before returning status.
    if ((header.flags&MH_DYLIB_IN_CACHE) && (address < base || address-base >= length)) return false;
  }
  return MacOSImageEvents::read(last) && normalize(last) && first.count == last.count && first.revision == last.revision &&
    std::equal(first.addresses.begin(),first.addresses.begin()+first.count,last.addresses.begin());
}
struct Process {
  dyld_process_s* value; const MacOSCacheCalls& calls;
  ~Process() { if (value) calls.dispose(value); }
};
struct Snapshot {
  dyld_process_snapshot_s* value; const MacOSCacheCalls& calls;
  ~Snapshot() { if (value) calls.release(value); }
};
}
MacOSCacheCalls macos_cache_calls() noexcept {
  MacOSCacheCalls c{}; c.pid = ::getpid;
  c.create = symbol<decltype(c.create)>("dyld_process_create_for_current_task");
  c.dispose = symbol<decltype(c.dispose)>("dyld_process_dispose");
  c.snapshot = symbol<decltype(c.snapshot)>("dyld_process_snapshot_create_for_process");
  c.release = symbol<decltype(c.release)>("dyld_process_snapshot_dispose");
  c.cache = symbol<decltype(c.cache)>("dyld_process_snapshot_get_shared_cache");
  c.images = symbol<decltype(c.images)>("dyld_shared_cache_for_each_image");
  c.segments = symbol<decltype(c.segments)>("dyld_image_for_each_segment_info");
  c.uuid = symbol<decltype(c.uuid)>("dyld_shared_cache_copy_uuid");
  c.base = symbol<decltype(c.base)>("dyld_shared_cache_get_base_address");
  c.size = symbol<decltype(c.size)>("dyld_shared_cache_get_mapped_size"); c.preflight = preflight; return c;
}
MacOSPlatformOrigins::MacOSPlatformOrigins(ImageSnapshotSource& images, MappingSource& mappings) noexcept
  : MacOSPlatformOrigins(images,mappings,macos_cache_calls()) {}
MacOSPlatformOrigins::MacOSPlatformOrigins(ImageSnapshotSource& images, MappingSource& mappings, MacOSCacheCalls calls, InspectionControl* control) noexcept
  : images_(images), mappings_(&mappings), calls_(calls), control_(control) { initialize(); }
MacOSPlatformOrigins::MacOSPlatformOrigins(ImageSnapshotSource& images, SliceBindingSource& slices) noexcept
  : MacOSPlatformOrigins(images,slices,macos_cache_calls()) {}
MacOSPlatformOrigins::MacOSPlatformOrigins(ImageSnapshotSource& images, SliceBindingSource& slices, MacOSCacheCalls calls, InspectionControl* control) noexcept
  : images_(images), slices_(&slices), calls_(calls), control_(control) { initialize(); }
bool MacOSPlatformOrigins::active(InspectionStep step) noexcept {
  if (failure_ != PlatformOriginFailure::none) return false;
  return inspect_continue(control_,step) || fail(PlatformOriginFailure::cancelled);
}
void MacOSPlatformOrigins::initialize() noexcept {
  if (!active(InspectionStep::preparation)) return;
  if (!calls_.pid || !calls_.create || !calls_.dispose || !calls_.snapshot || !calls_.release || !calls_.cache ||
      !calls_.images || !calls_.segments || !calls_.uuid || !calls_.base || !calls_.size || !calls_.preflight) { fail(PlatformOriginFailure::api); return; }
  owner_ = calls_.pid();
  if (owner_ <= 0) { fail(PlatformOriginFailure::process); return; }
  if (prepare()) (void)stable();
}
bool MacOSPlatformOrigins::fail(PlatformOriginFailure why) noexcept {
  if (failure_ == PlatformOriginFailure::none) failure_ = why;
  loaded_ = {}; cache_ = {}; count_ = 0; return false;
}
bool MacOSPlatformOrigins::prepare() noexcept {
  if (!active(InspectionStep::preparation) || !calls_.preflight() || !active(InspectionStep::preparation)) return fail(PlatformOriginFailure::preflight);
  Process process{calls_.create(),calls_};
  if (!process.value) return fail(PlatformOriginFailure::process);
  // Materialize SPI lazy dependencies once before fixing the loader observation.
  for (unsigned pass=0;pass<2;++pass) {
    if (!active(InspectionStep::preparation)) return false;
    if (calls_.pid() != owner_) return fail(PlatformOriginFailure::process);
    if (pass && (!images_.read(loaded_) || !normalize(loaded_))) return fail(PlatformOriginFailure::loader);
    if (!active(InspectionStep::preparation) || !calls_.preflight() || !active(InspectionStep::preparation)) return fail(PlatformOriginFailure::preflight);
    kern_return_t status = KERN_FAILURE;
    Snapshot snapshot{calls_.snapshot(process.value,&status),calls_};
    if (!snapshot.value || status != KERN_SUCCESS) return fail(PlatformOriginFailure::snapshot);
    const auto cache = calls_.cache(snapshot.value);
    if (!cache) return fail(PlatformOriginFailure::cache);
    const auto base = calls_.base(cache), size = calls_.size(cache);
    if (!base || !size || size > UINT64_MAX-base) return fail(PlatformOriginFailure::cache);
    if (!pass) continue;
    uuid_t uuid{}; calls_.uuid(cache,&uuid);
    if (std::all_of(std::begin(uuid),std::end(uuid),[](auto b){return b == 0;})) return fail(PlatformOriginFailure::cache);
    cache_.base = base; cache_.size = size; std::copy(std::begin(uuid),std::end(uuid),cache_.uuid.begin());
    __block bool invalid = false;
    calls_.images(cache,^(dyld_image_s* image) {
      if (invalid) return;
      if (!active(InspectionStep::origin)) { invalid = true; return; }
      if (!image || count_ == catalog_.size()) { invalid = true; return; }
      __block unsigned texts = 0, segments = 0;
      __block std::uint64_t address = 0;
      const bool complete = calls_.segments(image,^(const char* name,std::uint64_t start,std::uint64_t length,int protection) {
        if (invalid) return;
      if (!active(InspectionStep::origin)) { invalid = true; return; }
        if (++segments > 256 || !name) { invalid = true; return; }
        if (std::strcmp(name,"__TEXT") != 0) return;
        ++texts; address = start;
        if (!length || !(protection&1) || start < base || start-base >= size || length > size-(start-base)) invalid = true;
      });
      if (!complete || invalid || texts != 1) { invalid = true; return; }
      catalog_[count_++] = address;
    });
    if (!active(InspectionStep::preparation) || invalid || !count_) return fail(PlatformOriginFailure::catalog);
    auto end = catalog_.begin()+count_; std::sort(catalog_.begin(),end);
    if (std::adjacent_find(catalog_.begin(),end) != end) return fail(PlatformOriginFailure::catalog);
  }
  return true;
}
bool MacOSPlatformOrigins::stable() noexcept {
  if (!active(InspectionStep::images)) return false;
  if (calls_.pid() != owner_) return fail(PlatformOriginFailure::process);
  ImageSnapshot now{};
  if (!images_.read(now) || !normalize(now)) return fail(PlatformOriginFailure::loader);
  if (calls_.pid() != owner_) return fail(PlatformOriginFailure::process);
  if (now.revision != loaded_.revision || now.count != loaded_.count ||
      !std::equal(now.addresses.begin(),now.addresses.begin()+now.count,loaded_.addresses.begin())) return fail(PlatformOriginFailure::changed);
  return active(InspectionStep::images);
}
bool MacOSPlatformOrigins::read(std::uintptr_t address, ImageOrigin& out) noexcept {
  out = {};
  if (!active(InspectionStep::origin) || !stable()) return false;
  if (!address || !std::binary_search(loaded_.addresses.begin(),loaded_.addresses.begin()+loaded_.count,address))
    return fail(PlatformOriginFailure::address);
  ImageOrigin result{};
  if (std::binary_search(catalog_.begin(),catalog_.begin()+count_,address)) {
    result.kind = ImageOriginKind::platform_cache; result.cache = cache_; result.cache.address = address;
  } else {
    auto& m = result.application;
    if (slices_) {
      SliceBinding binding{};
      if (!slices_->read(address,binding) || binding.mapping.address != address || !valid_slice_binding(binding)) return fail(PlatformOriginFailure::mapping);
      m = binding.mapping; result.slice = binding.slice;
    } else if (!mappings_->read(address,m) || m.address != address || !m.size || m.size > UINT64_MAX-m.address || m.offset || !valid_file(m.file))
        return fail(PlatformOriginFailure::mapping);
    result.kind = ImageOriginKind::application;
  }
  if (!active(InspectionStep::origin) || !stable()) return false;
  out = result; return true;
}
} // namespace sh3::observer
