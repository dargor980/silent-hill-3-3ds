#pragma once
#include "sh3_observer/image_identity.hpp"

namespace sh3::observer {
struct RegionVnode {
  std::uint64_t address{}, size{}, region_offset{};
  FileObject file{};
};
enum class VnodeQuery { found, no_vnode, submap, unavailable };
struct MacOSVnodeCalls {
  int (*pid)();
  int (*info)(int, int, std::uint64_t, void*, int);
};
// Point association only: neither resident-byte identity nor a file-offset proof.
class MacOSRegionVnodeSource final {
public:
  MacOSRegionVnodeSource() noexcept;
  explicit MacOSRegionVnodeSource(MacOSVnodeCalls) noexcept;
  VnodeQuery query(std::uint64_t, RegionVnode&) noexcept;
private:
  MacOSVnodeCalls calls_;
  int owner_{};
};
} // namespace sh3::observer
