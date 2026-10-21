#pragma once
#include "sh3/domain/render_scene.hpp"
#include "sh3/platform/stdio_files.hpp"
#include <cstddef>

namespace sh3::platform {
inline constexpr std::size_t inspection_max_vertices = 3072;
struct InspectionMesh {
    const domain::SceneVertex *data;
    std::size_t count;
};
[[nodiscard]] bool valid_inspection_mesh(InspectionMesh mesh) noexcept;
// Count is zero on failure; the destination may contain incomplete data.
[[nodiscard]] ports::FileError read_inspection_geometry(const char *path,
                                                        domain::SceneVertex *destination,
                                                        std::size_t capacity, std::size_t &count,
                                                        StdioApi api = system_stdio) noexcept;
} // namespace sh3::platform
