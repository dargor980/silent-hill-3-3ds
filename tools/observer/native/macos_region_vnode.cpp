#include "sh3_observer/macos_region_vnode.hpp"
#include <libproc.h>
#include <sys/proc_info.h>
#include <sys/stat.h>
#include <unistd.h>

namespace sh3::observer {
MacOSRegionVnodeSource::MacOSRegionVnodeSource() noexcept
  : MacOSRegionVnodeSource({::getpid, ::proc_pidinfo}) {}
MacOSRegionVnodeSource::MacOSRegionVnodeSource(MacOSVnodeCalls calls) noexcept
  : calls_(calls), owner_(calls.pid ? calls.pid() : 0) {}
VnodeQuery MacOSRegionVnodeSource::query(std::uint64_t address, RegionVnode& output) noexcept {
  output = {};
  if (!address || !calls_.pid || !calls_.info || owner_ <= 0 || calls_.pid() != owner_)
    return VnodeQuery::unavailable;
  proc_regionwithpathinfo r{};
  const auto size = static_cast<int>(sizeof(r));
  const auto got = calls_.info(owner_, PROC_PIDREGIONPATHINFO, address, &r, size);
  if (calls_.pid() != owner_ || got != size) return VnodeQuery::unavailable;
  const auto& region = r.prp_prinfo;
  if (!region.pri_size || region.pri_address > UINT64_MAX-region.pri_size ||
      address < region.pri_address || address >= region.pri_address+region.pri_size ||
      region.pri_offset > UINT64_MAX-region.pri_size) return VnodeQuery::unavailable;
  if (region.pri_flags & PROC_REGION_SUBMAP) return VnodeQuery::submap;
  const auto& s = r.prp_vip.vip_vi.vi_stat;
  if (!s.vst_mode && !s.vst_dev && !s.vst_ino && !s.vst_size && !s.vst_mtime &&
      !s.vst_ctime && !s.vst_mtimensec && !s.vst_ctimensec) return VnodeQuery::no_vnode;
  if (!S_ISREG(s.vst_mode) || s.vst_size <= 0 || s.vst_mtimensec < 0 || s.vst_ctimensec < 0 ||
      s.vst_mtimensec >= 1000000000 || s.vst_ctimensec >= 1000000000) return VnodeQuery::unavailable;
  FileObject file{s.vst_dev, s.vst_ino, static_cast<std::uint64_t>(s.vst_size),
    s.vst_mtime, s.vst_ctime, static_cast<std::uint32_t>(s.vst_mtimensec), static_cast<std::uint32_t>(s.vst_ctimensec)};
  if (!valid_file(file)) return VnodeQuery::unavailable;
  output = {region.pri_address, region.pri_size, region.pri_offset, file};
  return VnodeQuery::found;
}
} // namespace sh3::observer
