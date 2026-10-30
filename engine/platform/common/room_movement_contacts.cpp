#include "sh3/platform/room_movement_contacts.hpp"

namespace sh3::platform {
domain::RoomContactError RoomMovementContacts::prepare(const domain::RoomContactInput &input,
                                                       domain::RoomContactMemory memory) noexcept {
    return scene_.prepare(input, memory);
}
ports::MovementContactStatus RoomMovementContacts::resolve(
    const ports::MovementContactQuery &query, domain::Vec3 &accepted) const noexcept {
    const auto error = scene_.resolve(query.from, query.requested, accepted);
    if (error == domain::RoomContactError::ok) return ports::MovementContactStatus::accepted;
    if (error == domain::RoomContactError::unavailable) return ports::MovementContactStatus::unavailable;
    return ports::MovementContactStatus::unsupported;
}
} // namespace sh3::platform
