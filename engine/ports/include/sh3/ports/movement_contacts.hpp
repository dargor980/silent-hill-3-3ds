#pragma once
#include "sh3/domain/render_scene.hpp"
#include <cstdint>

namespace sh3::ports {
struct MovementContactQuery {
    domain::Vec3 from{}, requested{}; // Absolute original units, including Y.
    std::uint32_t ordinal{}; // Proposed update, not a committed gameplay event.
};
enum class MovementContactStatus { accepted, unavailable, unsupported };
class IMovementContacts {
  public:
    virtual ~IMovementContacts() = default;
    // Read-only query against a stable world. May be repeated after an animation failure.
    // No irreversible effects/consumption. On accepted, write ALL three coordinates.
    // Adapter owns geometry validation and the supported physical profile.
    [[nodiscard]] virtual MovementContactStatus resolve(
        const MovementContactQuery &, domain::Vec3 &accepted) const noexcept = 0;
};
} // namespace sh3::ports
