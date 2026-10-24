#pragma once
#include "sh3/domain/inspection_rig.hpp"
#include "sh3/platform/stdio_files.hpp"

namespace sh3::platform {
[[nodiscard]] ports::FileError read_inspection_rig(const char *, domain::InspectionRig &,
                                                   StdioApi = system_stdio) noexcept;
// Exact length and CRC are bound by the validated SRI1 material; failed pixels are unusable.
[[nodiscard]] ports::FileError read_rig_texture(const char *, const domain::RigMaterial &,
                                                std::uint8_t *, std::size_t,
                                                StdioApi = system_stdio) noexcept;
// Raw PS2 RGBA -> ABGR/Morton; normalize alpha once. No vertical flip.
[[nodiscard]] bool upload_rig_texture(const domain::RigMaterial &, const std::uint8_t *,
                                      std::size_t, std::uint8_t *, std::size_t) noexcept;
} // namespace sh3::platform
