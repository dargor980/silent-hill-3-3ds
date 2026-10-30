#include "sh3/platform/room_runtime.hpp"
#include "sh3/domain/inspection_movement.hpp"
#include "sh3/platform/inspection_crc32.hpp"
#include "sh3/platform/inspection_rig.hpp"
#include <array>
#include <cerrno>
#include <cstring>
#include <new>

namespace sh3::platform {
namespace {
using E = ports::FileError;
using Result = LocomotionLoadResult;
bool join(const char *root, const char *name, std::array<char, 512> &out) noexcept {
    if (!root || !*root || std::strlen(root) > 450)
        return false;
    const auto separator = root[std::strlen(root) - 1] == '/' ? "" : "/";
    const auto n = std::snprintf(out.data(), out.size(), "%s%s%s", root, separator, name);
    return n > 0 && std::size_t(n) < out.size();
}
std::uint32_t word(const std::uint8_t *p) noexcept {
    return std::uint32_t(p[0]) | (std::uint32_t(p[1]) << 8) | (std::uint32_t(p[2]) << 16) |
           (std::uint32_t(p[3]) << 24);
}
float number(const std::uint8_t *p) noexcept {
    auto bits = word(p);
    float f;
    std::memcpy(&f, &bits, 4);
    return f;
}
// Streaming CRC; a fixed limit prevents accidental reads of an unbounded SD resource.
E checked_file(const char *path, std::uint32_t expected, StdioApi api,
               std::size_t expected_size = 0) noexcept {
    auto *file = api.open(path, "rb");
    if (!file)
        return E::read_failed;
    std::array<std::uint8_t, 4096> block{};
    std::uint32_t crc = 0;
    std::size_t total = 0;
    E result = E::ok;
    for (;;) {
        auto count = api.read(block.data(), 1, block.size(), file);
        if (api.error(file)) {
            result = E::read_failed;
            break;
        }
        total += count;
        if (total > 2 * 1024 * 1024) {
            result = E::invalid_data;
            break;
        }
        crc = inspection_crc32(block.data(), count, crc);
        if (count < block.size())
            break;
    }
    if (result == E::ok && expected_size && total != expected_size)
        result = E::invalid_data;
    if (result == E::ok && crc != expected)
        result = E::verify_failed;
    if (api.close(file) && result == E::ok)
        result = E::close_failed;
    return result;
}
} // namespace
Result read_room_runtime(const char *root, std::unique_ptr<RoomAssets> &out,
                         StdioApi api) noexcept {
    std::array<char, 512> path{};
    if (!join(root, "scene.srr", path))
        return {E::invalid_target, "ROOM_PATH"};
    auto *file = api.open(path.data(), "rb");
    if (!file)
        return {E::read_failed, "ROOM_OPEN"};
    std::array<std::uint8_t, 596> wire{};
    auto count = api.read(wire.data(), 1, wire.size(), file);
    std::uint8_t extra{};
    auto tail = api.read(&extra, 1, 1, file);
    E error = api.error(file)                ? E::read_failed
              : count != wire.size() || tail ? E::invalid_data
                                             : E::ok;
    if (api.close(file) && error == E::ok)
        error = E::close_failed;
    if (error != E::ok)
        return {error, "ROOM_READ"};
    const auto *h = wire.data(), *p = h + 32;
    if (std::memcmp(h, "S3RRv1\0\0", 8) || word(h + 8) != 564 || word(h + 28) != 1 ||
        word(p) != 32 || inspection_crc32(p, 564) != word(h + 12))
        return {E::invalid_data, "ROOM_HEADER"};
    std::unique_ptr<RoomAssets> candidate(new (std::nothrow) RoomAssets{});
    if (!candidate)
        return {E::read_failed, "ROOM_ALLOC"};
    domain::RoomContactInput input;
    input.origin = {number(p + 4), number(p + 8), number(p + 12)};
    input.floor_y = number(p + 16);
    input.floor = {number(p + 20), number(p + 24), number(p + 28), number(p + 32)};
    candidate->spawn = {number(p + 36), number(p + 40), number(p + 44)};
    candidate->yaw = number(p + 48);
    std::array<domain::RoomContactBox, 32> boxes{};
    for (unsigned i = 0; i < 32; ++i) {
        const auto *b = p + 52 + i * 16;
        boxes[i] = {number(b), number(b + 4), number(b + 8), number(b + 12)};
    }
    input.blockers = boxes.data();
    input.blocker_count = boxes.size();
    domain::Vec3 accepted{};
    domain::PoseMatrix instance{};
    if (input.origin.x != domain::room_origin.x || input.origin.y != 0 ||
        input.origin.z != domain::room_origin.z || input.floor_y != 0 ||
        candidate->contacts.prepare(input) != domain::RoomContactError::ok ||
        candidate->contacts.resolve({candidate->spawn, candidate->spawn, 0}, accepted) !=
            ports::MovementContactStatus::accepted ||
        !domain::make_inspection_movement_model(candidate->spawn, candidate->yaw, instance))
        return {E::invalid_data, "ROOM_SPAWN"};
    join(root, "map.srm", path);
    error = read_room_map(path.data(), candidate->map, api);
    if (error == E::ok)
        error = checked_file(path.data(), word(h + 16), api);
    if (error != E::ok)
        return {error, "ROOM_MAP"};
    if (candidate->map.shape_count != 31 || candidate->map.glass_crc != word(h + 24))
        return {E::invalid_data, "ROOM_PROFILE"};
    const auto loaded = read_locomotion_bundle(root, candidate->rig, api);
    if (loaded.error != E::ok)
        return loaded;
    join(root, "heather.sri", path);
    error = checked_file(path.data(), word(h + 20), api);
    if (error != E::ok)
        return {error, "ROOM_SRI"};
    domain::RoomMemory memory;
    if (candidate->rig.shared.material_count != 13 ||
        !domain::room_memory(candidate->map, candidate->rig.shared, memory) ||
        memory.total + room_runtime_extra > 64 * 1024 * 1024)
        return {E::invalid_data, "ROOM_BUDGET"};
    join(root, "glass.rgba", path);
    error = checked_file(path.data(), word(h + 24), api);
    if (error != E::ok)
        return {error, "ROOM_GLASS"};
    for (unsigned i = 0; i < candidate->map.material_count; ++i) {
        char name[32];
        std::snprintf(name, sizeof(name), "room-texture-%02u.rgba", i);
        join(root, name, path);
        error = checked_file(path.data(), candidate->map.materials[i].crc, api, 512 * 512 * 4);
        if (error != E::ok)
            return {error, "ROOM_TEXTURE"};
    }
    out.swap(candidate); // All readers/CRC/budgets/spawn succeeded; old scene released last.
    return {};
}
bool RoomTextures::read(const domain::RigMaterial &m, std::uint8_t *out,
                        std::size_t size) noexcept {
    std::array<char, 512> path{};
    char name[32];
    if (m.texture == 13)
        std::snprintf(name, sizeof(name), "glass.rgba");
    else if (m.texture < 13)
        std::snprintf(name, sizeof(name), "texture-%02u.rgba", unsigned(m.texture));
    else if (m.texture < 14 + domain::room_materials)
        std::snprintf(name, sizeof(name), "room-texture-%02u.rgba", unsigned(m.texture - 14));
    else
        return false;
    return join(directory_, name, path) &&
           read_rig_texture(path.data(), m, out, size, api_) == E::ok;
}
} // namespace sh3::platform
