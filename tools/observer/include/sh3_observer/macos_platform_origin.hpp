#pragma once
#include "sh3_observer/platform_inventory.hpp"
#include "sh3_observer/inspection_control.hpp"
#include <mach/kern_return.h>
#include <uuid/uuid.h>

// Opaque SPI handles. No implementation or ownership is exposed here.
struct dyld_process_s; struct dyld_process_snapshot_s;
struct dyld_shared_cache_s; struct dyld_image_s;
namespace sh3::observer {
struct MacOSCacheCalls {
  int (*pid)();
  dyld_process_s* (*create)();
  void (*dispose)(dyld_process_s*);
  dyld_process_snapshot_s* (*snapshot)(dyld_process_s*, kern_return_t*);
  void (*release)(dyld_process_snapshot_s*);
  dyld_shared_cache_s* (*cache)(dyld_process_snapshot_s*);
  void (*images)(dyld_shared_cache_s*, void(^)(dyld_image_s*));
  bool (*segments)(dyld_image_s*, void(^)(const char*, std::uint64_t, std::uint64_t, int));
  void (*uuid)(dyld_shared_cache_s*, uuid_t*);
  std::uint64_t (*base)(dyld_shared_cache_s*);
  std::uint64_t (*size)(dyld_shared_cache_s*);
  bool (*preflight)();
};
MacOSCacheCalls macos_cache_calls() noexcept;
inline constexpr std::size_t platform_cache_capacity = 32768;
enum class PlatformOriginFailure { none, api, process, snapshot, cache, catalog, loader, changed, address, mapping, preflight, cancelled };
// Single owner. A loader event ends this session; create a new instance explicitly.
class MacOSPlatformOrigins final : public ImageOriginSource {
public:
  MacOSPlatformOrigins(ImageSnapshotSource&, MappingSource&) noexcept;
  MacOSPlatformOrigins(ImageSnapshotSource&, MappingSource&, MacOSCacheCalls, InspectionControl* = nullptr) noexcept;
  MacOSPlatformOrigins(ImageSnapshotSource&, SliceBindingSource&) noexcept;
  MacOSPlatformOrigins(ImageSnapshotSource&, SliceBindingSource&, MacOSCacheCalls, InspectionControl* = nullptr) noexcept;
  MacOSPlatformOrigins(const MacOSPlatformOrigins&) = delete;
  MacOSPlatformOrigins& operator=(const MacOSPlatformOrigins&) = delete;
  bool read(std::uintptr_t, ImageOrigin&) noexcept override;
  PlatformOriginFailure failure() const noexcept { return failure_; }
  std::size_t catalog_size() const noexcept { return count_; }
private:
  void initialize() noexcept;
  bool prepare() noexcept;
  bool stable() noexcept;
  bool fail(PlatformOriginFailure) noexcept;
  bool active(InspectionStep) noexcept;
  ImageSnapshotSource& images_;
  MappingSource* mappings_{};
  SliceBindingSource* slices_{};
  const MacOSCacheCalls calls_;
  InspectionControl* control_{};
  int owner_{};
  ImageSnapshot loaded_{};
  CacheImage cache_{};
  std::array<std::uint64_t,platform_cache_capacity> catalog_{};
  std::size_t count_{};
  PlatformOriginFailure failure_{PlatformOriginFailure::none};
};
} // namespace sh3::observer
