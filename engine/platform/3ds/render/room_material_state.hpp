#pragma once
#include "sh3/domain/room_scene.hpp"
namespace sh3::platform::ctr {
// Set every relevant state explicitly; unsupported pass changes nothing.
[[nodiscard]] bool bind_room_material(domain::RoomPass) noexcept;
} // namespace sh3::platform::ctr
