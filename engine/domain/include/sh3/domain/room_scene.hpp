#pragma once
#include "sh3/domain/inspection_rig.hpp"

namespace sh3::domain {
inline constexpr Vec3 room_origin{100000, 0, 140000};
inline constexpr float room_scale = .002F;
inline constexpr std::size_t room_shapes = 31, room_vertices = 27900, room_glass_vertices = 96;
inline constexpr std::size_t room_dynamic_vertices = rig_indices + room_glass_vertices;
inline constexpr std::size_t room_transparent_triangles = room_dynamic_vertices / 3;
inline constexpr std::size_t room_materials = 9;
enum class RoomPass : std::uint32_t {
    neutral,
    opaque,
    glass,
    hair,
    map_opaque,
    map_cutout,
    map_blend
};
constexpr bool room_map_pass(RoomPass p) noexcept {
    return p == RoomPass::map_opaque || p == RoomPass::map_cutout || p == RoomPass::map_blend;
}
struct RoomMapMaterial {
    std::uint32_t width{}, height{}, crc{};
    RoomPass pass{};
};
struct RoomShape {
    std::uint32_t offset{}, first{}, count{}, glass{}, material{}, visible{1};
};
struct RoomMap {
    std::uint32_t shape_count{}, vertex_count{}, glass_crc{}, material_count{};
    std::array<RoomMapMaterial, room_materials> materials{};
    std::array<RoomShape, room_shapes> shapes{};
    // Already in the common render basis. The loader applies MAP T(O) once.
    std::array<CharacterDrawVertex, room_vertices> vertices{};
};
struct RoomCamera {
    Vec3 eye, target;
    float fov, near_plane, far_plane;
};
struct RoomRange {
    RoomPass pass{};
    std::uint32_t first{}, count{}, texture{}; // neutral uses the static MAP buffer.
};
struct RoomFrame {
    std::uint32_t vertex_count{}, range_count{};
    std::array<CharacterDrawVertex, room_dynamic_vertices> vertices{};
    std::array<RoomRange, room_shapes + rig_materials + room_transparent_triangles> ranges{};
};
struct RoomTriangle {
    double depth{};
    std::uint32_t first{}, material{};
};
struct RoomWorkspace {
    RigPalette palette{};
    std::array<RigVertexScratch, rig_vertices> vertices{};
    std::array<RoomTriangle, room_transparent_triangles> order{};
};
struct RoomMemory {
    std::size_t textures{}, texture_staging{}, map_resident{}, dynamic_resident{},
        model_and_scratch{}, loader_staging{}, platform_reserve{}, total{};
};
// Column-major instance, original units; preserve W. No individual centering or division.
[[nodiscard]] std::array<float, 4> room_position(const PoseMatrix &,
                                                 const std::array<float, 4> &) noexcept;
[[nodiscard]] RoomCamera room_camera() noexcept;
[[nodiscard]] bool valid_room_vertex(const CharacterDrawVertex &) noexcept;
[[nodiscard]] bool valid_room_map(const RoomMap &) noexcept;
// One-time diagnostic appearance for a validated map. vertices must be a distinct
// copy of map.vertices with at least map.vertex_count entries. Only neutral RGB
// changes; geometry, UV, glass and the immutable source remain untouched. No heap.
void room_diagnostic_colors(const RoomMap &, CharacterDrawVertex *vertices) noexcept;
[[nodiscard]] bool room_memory(const InspectionRig &, RoomMemory &) noexcept;
[[nodiscard]] bool room_memory(const RoomMap &, const InspectionRig &, RoomMemory &) noexcept;
// Borrowed assets must outlive this object and remain immutable. Validate once
// at construction; each frame still validates the changing pose and instance.
class PreparedRoomScene final {
  public:
    PreparedRoomScene(const RoomMap &, const InspectionRig &) noexcept;
    bool ready() const noexcept { return ready_; }
    const RoomMemory &memory() const noexcept { return memory_; }
    [[nodiscard]] bool frame(const RigPose &, const PoseMatrix &, RoomWorkspace &,
                             RoomFrame &) const noexcept;

  private:
    const RoomMap &map_;
    const InspectionRig &model_;
    RoomMemory memory_{};
    bool ready_{};
};
// Validated immutable model/map; caller owns distinct out/workspace. Failure preserves out.
// Internal MAP ranges preserve source order. Glass/hair retain global depth sorting.
[[nodiscard]] bool room_frame(const RoomMap &, const InspectionRig &, const RigPose &,
                              const PoseMatrix &instance, RoomWorkspace &, RoomFrame &) noexcept;
} // namespace sh3::domain
