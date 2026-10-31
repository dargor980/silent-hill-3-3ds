#pragma once
#include "sh3/application/movement_controller.hpp"
#include "sh3/ports/room_view.hpp"

namespace sh3::application {
enum class RoomFault { none, spawn, simulation, render };
class RoomLoop final : public IMovementSession {
  public:
    RoomLoop(const domain::LocomotionProfile &, const domain::LocomotionSkeleton &,
             const domain::LocomotionSampleReader &, const ports::IMovementContacts &,
             ports::IRoomView &, domain::Vec3 spawn, float yaw) noexcept;
    unsigned step(MovementInput, std::uint64_t elapsed_us) noexcept override;
    void dispatch(domain::LifecycleEvent) noexcept override;
    domain::SessionState state() const noexcept override { return controller_.state(); }
    bool awaiting_release() const noexcept override { return controller_.awaiting_release(); }
    const InspectionActorSnapshot &snapshot() const noexcept { return controller_.snapshot(); }
    const MovementController &controller() const noexcept { return controller_; }
    RoomFault fault() const noexcept { return fault_; }
    ports::RenderResult render_result() const noexcept { return render_result_; }
    bool ready() const noexcept { return published_ && controller_.ready(); }
    void trace(domain::WorkTrace *value) noexcept {
        trace_ = value;
        controller_.trace(value);
    }

  private:
    bool valid_spawn() const noexcept;
    void fail(RoomFault) noexcept;
    MovementController controller_;
    const ports::IMovementContacts &contacts_;
    ports::IRoomView &view_;
    domain::Vec3 spawn_;
    RoomFault fault_{RoomFault::none};
    ports::RenderResult render_result_{ports::RenderResult::busy};
    bool published_{}, busy_{};
    domain::WorkTrace *trace_{};
};
static_assert(sizeof(RoomLoop) + 256 <= 32 * 1024, "Room loop and HID exceed controller budget");
} // namespace sh3::application
