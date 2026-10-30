#include "sh3/application/room_loop.hpp"
#include <limits>

namespace sh3::application {
namespace {
using S = domain::SessionState;
using E = domain::LifecycleEvent;
using R = ports::RenderResult;
struct Guard {
    bool &busy;
    explicit Guard(bool &b) noexcept : busy(b) { busy = true; }
    ~Guard() { busy = false; }
};
} // namespace
RoomLoop::RoomLoop(const domain::LocomotionProfile &p, const domain::LocomotionSkeleton &s,
                   const domain::LocomotionSampleReader &r, const ports::IMovementContacts &c,
                   ports::IRoomView &v, domain::Vec3 spawn, float yaw) noexcept
    : controller_(p, s, r, c, spawn, yaw), contacts_(c), view_(v), spawn_(spawn) {
    published_ = valid_spawn() && controller_.ready();
    if (!published_)
        fail(controller_.ready() ? RoomFault::spawn : RoomFault::simulation);
}
bool RoomLoop::valid_spawn() const noexcept {
    const auto nan = std::numeric_limits<float>::quiet_NaN();
    domain::Vec3 accepted{nan, nan, nan};
    return contacts_.resolve({spawn_, spawn_, 0}, accepted) ==
               ports::MovementContactStatus::accepted &&
           accepted.x == spawn_.x && accepted.y == spawn_.y && accepted.z == spawn_.z;
}
void RoomLoop::fail(RoomFault fault) noexcept {
    fault_ = fault;
    controller_.pause_on_fault();
}
void RoomLoop::dispatch(E event) noexcept {
    if (busy_)
        return;
    const Guard guard(busy_);
    // A latched fault requires a neutral sample followed by L, never a blind resume.
    if (fault_ != RoomFault::none && event == E::toggle_pause)
        return;
    controller_.dispatch(event);
}
unsigned RoomLoop::step(MovementInput input, std::uint64_t elapsed) noexcept {
    if (busy_)
        return 0;
    const Guard guard(busy_);
    render_result_ = R::busy;
    unsigned committed = 0;
    if (input.quit || state() == S::stopped || state() == S::suspended) {
        controller_.step(input, 0);
        return 0;
    }
    if (!awaiting_release() && input.restart && !input.pause) {
        if (!valid_spawn())
            fail(RoomFault::spawn);
        else {
            controller_.step(input, 0);
            if (controller_.result().error == InspectionActorError::ok) {
                fault_ = RoomFault::none;
                published_ = true;
            } else
                fail(RoomFault::simulation);
        }
    } else if (fault_ == RoomFault::none || awaiting_release()) {
        committed = controller_.step(input, elapsed);
        if (fault_ == RoomFault::none && controller_.result().error != InspectionActorError::ok)
            fail(RoomFault::simulation);
    }
    // Contact/sample errors still display the last complete snapshot. GPU failure is
    // latched until L: no automatic retry storm or simulation hidden behind a stale image.
    if (ready() && fault_ != RoomFault::render) {
        render_result_ = view_.present(snapshot().animation.model, snapshot().instance);
        if (render_result_ == R::unavailable || render_result_ == R::invalid_camera)
            fail(RoomFault::render);
    }
    return committed;
}
} // namespace sh3::application
