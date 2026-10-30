#pragma once
#include "sh3/domain/room_contacts.hpp"
#include "sh3/ports/movement_contacts.hpp"

namespace sh3::platform {
class RoomMovementContacts final : public ports::IMovementContacts {
  public:
    [[nodiscard]] domain::RoomContactError prepare(const domain::RoomContactInput &input,
                                                  domain::RoomContactMemory memory = {}) noexcept;
    [[nodiscard]] ports::MovementContactStatus resolve(const ports::MovementContactQuery &,
                                                       domain::Vec3 &accepted) const noexcept override;
    bool ready() const noexcept { return scene_.ready(); }
  private:
    domain::RoomContactScene scene_{};
};
static_assert(sizeof(RoomMovementContacts) <= domain::room_contact_resident_bound);
} // namespace sh3::platform
