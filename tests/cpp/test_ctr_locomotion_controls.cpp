#include "check.hpp"
// Compile the actual entry point/HID mapping/APT hook, with host SDK services.
#define main sh3_heather_entry
#include "../../engine/platform/3ds/render/rig_main.cpp"
#undef main

namespace fake {
void (*hook)(APT_HookType, void *){};
void *context{};
aptHookCookie *cookie{};
unsigned fast_on{}, fast_off{}, screens{}, unhooks{};
bool new_model{true};
Result model_result{};
std::uint64_t ticks{};
} // namespace fake
void aptHook(aptHookCookie *cookie, void (*hook)(APT_HookType, void *), void *context) {
    CHECK(!fake::hook);
    fake::hook = hook;
    fake::context = context;
    fake::cookie = cookie;
}
void aptUnhook(aptHookCookie *cookie) {
    CHECK(fake::cookie == cookie);
    fake::hook = nullptr;
    ++fake::unhooks;
}
bool aptMainLoop() { return false; }
Result APT_CheckNew3DS(bool *value) {
    *value = fake::new_model;
    return fake::model_result;
}
void osSetSpeedupEnable(bool enabled) { enabled ? ++fake::fast_on : ++fake::fast_off; }
void gfxInitDefault() { ++fake::screens; }
void gfxExit() { --fake::screens; }
void consoleInit(int screen, void *) { CHECK(screen == GFX_BOTTOM); }
void gfxFlushBuffers() {}
void gfxSwapBuffers() {}
void gspWaitForVBlank() {}
void hidScanInput() {}
u32 hidKeysHeld() { return 0; }
u32 hidKeysDown() { return 0; }
std::uint64_t svcGetSystemTick() { return fake::ticks++; }
float C3D_GetDrawingTime() { return 1; }

namespace {
struct Reader final : sh3::domain::LocomotionSampleReader {
    bool read(std::uint32_t, std::uint32_t, std::uint32_t,
              sh3::domain::LocomotionTransform &out) const noexcept override {
        out = {{0, 0, 0}, {0, 0, 0, 1}};
        return true;
    }
};
struct Scene final : sh3::ports::IRigScene {
    sh3::ports::RenderResult present_pose(const sh3::domain::OrbitCamera &,
                                          const sh3::domain::RigPose &) noexcept override {
        return sh3::ports::RenderResult::presented;
    }
};
} // namespace
int main() {
    using namespace sh3;
    Scene scene;
    Reader reader;
    domain::LocomotionSkeleton rig{};
    rig.bone_count = 2;
    rig.parents[0] = -1;
    rig.parents[1] = 0;
    rig.channels[0] = 1;
    rig.channels[1] = 2;
    application::LocomotionProbe app(scene, domain::heather_locomotion_profile, rig, reader);
    // Only down edges select clips or toggle pause; held buttons still guard resume.
    step_controls(app, KEY_ZR, 0, 0);
    CHECK(!app.pending_clip());
    step_controls(app, KEY_ZL | KEY_ZR, KEY_ZL | KEY_ZR, 0);
    CHECK(app.notice() == application::LocomotionNotice::selection_conflict);
    step_controls(app, KEY_ZL, KEY_ZL, 0);
    CHECK(app.error() == domain::LocomotionError::unsupported_transition);
    step_controls(app, KEY_ZR, KEY_ZR, 0);
    CHECK(app.pending_clip() == 109);
    step_controls(app, KEY_ZR, 0, .04F);
    CHECK(app.snapshot().clock.target_id == 109);
    step_controls(app, KEY_A, KEY_A, .04F);
    CHECK(app.paused());
    step_controls(app, KEY_A, 0, .04F);
    CHECK(app.paused());
    step_controls(app, KEY_R, KEY_R, .1F);
    CHECK(app.snapshot().clock.blend == 1536);
    step_controls(app, KEY_L, KEY_L, .1F);
    CHECK(app.snapshot().clock.mode == domain::LocomotionMode::stable && app.paused());
    step_controls(app, KEY_SELECT, KEY_SELECT, 0);
    CHECK(app.face_view());
    step_controls(app, KEY_X | KEY_DUP | KEY_DRIGHT, 0, .1F);
    CHECK(app.view().camera().distance < .65F && app.view().camera().yaw > 0);
    CHECK(app.view().camera().elevation > .1F);
    const auto distance = app.view().camera().distance;
    step_controls(app, KEY_Y | KEY_DDOWN | KEY_DLEFT, 0, .1F);
    CHECK(app.view().camera().distance > distance && app.view().camera().yaw == 0);
    step_controls(app, KEY_B, KEY_B, 0);
    CHECK(!app.face_view() && app.view().camera().distance == 3);
    platform::FrameCadence cadence(100);
    {
        Screens screens;
        CHECK(screens.fast_requested() && fake::fast_on == 1);
        Hook hook(app, cadence, screens.fast_requested());
        for (auto sleep : {APTHOOK_ONSUSPEND, APTHOOK_ONSLEEP}) {
            cadence.record(0, true);
            cadence.record(100, true);
            CHECK(cadence.fps().has_value());
            fake::hook(sleep, fake::context);
            CHECK(!cadence.fps() && app.view().state() == domain::SessionState::suspended);
            fake::hook(sleep == APTHOOK_ONSLEEP ? APTHOOK_ONWAKEUP : APTHOOK_ONRESTORE,
                       fake::context);
            CHECK(app.view().awaiting_release() && app.paused());
            step_controls(app, KEY_ZR, 0, 3600);
            CHECK(app.view().awaiting_release() && !app.pending_clip());
            step_controls(app, 0, 0, 3600);
            CHECK(!app.view().awaiting_release() && app.snapshot().clock.counter == 0);
        }
        CHECK(fake::fast_on == 3);
        fake::hook(APTHOOK_ONEXIT, fake::context);
        CHECK(app.view().state() == domain::SessionState::stopped);
    }
    CHECK(fake::fast_off == 1 && fake::screens == 0 && fake::unhooks == 1);
    for (bool is_new : {false, true}) {
        fake::new_model = is_new;
        fake::model_result = is_new ? -1 : 0;
        Screens screens;
        CHECK(!screens.fast_requested());
        application::LocomotionProbe a(scene, domain::heather_locomotion_profile, rig, reader);
        Hook hook(a, cadence, false);
        fake::hook(APTHOOK_ONSLEEP, fake::context);
        fake::hook(APTHOOK_ONWAKEUP, fake::context);
        step_controls(a, KEY_START, KEY_START, .1F);
        CHECK(a.view().state() == domain::SessionState::stopped);
    }
    CHECK(fake::fast_on == 3 && fake::fast_off == 1 && fake::screens == 0 && !fake::hook);
    std::puts("Actual Heather entry point: HID mapping, APT hooks, CPU mode and teardown OK");
}
