#include "room_main.hpp"
#include "../movement_controls.hpp"
#include "room_renderer.hpp"
#include "sh3/application/room_loop.hpp"
#include "sh3/platform/frame_cadence.hpp"
#include "sh3/platform/skinning_capture.hpp"
#include <cstdio>
#include <new>

namespace sh3::platform::ctr {
namespace {
using S = domain::SessionState;
struct Screens {
    bool fast{};
    Screens() {
        gfxInitDefault();
        consoleInit(GFX_BOTTOM, nullptr);
        bool is_new = false;
        fast = R_SUCCEEDED(APT_CheckNew3DS(&is_new)) && is_new;
        if (fast)
            osSetSpeedupEnable(true);
    }
    ~Screens() {
        if (fast)
            osSetSpeedupEnable(false);
        gfxExit();
    }
};
class Retry final : public application::IMovementSession {
  public:
    explicit Retry(bool choose = false) : choosing(choose) {}
    unsigned step(application::MovementInput input, std::uint64_t) noexcept override {
        if (input.quit)
            lifecycle.apply(domain::LifecycleEvent::quit);
        if (state() == S::suspended || state() == S::stopped)
            return 0;
        if (release)
            release = input.any_held;
        else if ((input.restart && !input.pause) || (choosing && input.pause && !input.restart)) {
            hybrid = input.restart;
            retry = true;
            lifecycle.apply(domain::LifecycleEvent::quit);
        }
        return 0;
    }
    void dispatch(domain::LifecycleEvent event) noexcept override {
        const auto before = state();
        lifecycle.apply(event);
        if (state() != before)
            release = true;
    }
    S state() const noexcept override { return lifecycle.state(); }
    bool awaiting_release() const noexcept override { return release; }
    domain::Lifecycle lifecycle;
    bool release{true}, retry{}, choosing{}, hybrid{};
};
bool retry_screen(const char *reason, bool fast) {
    std::printf("\x1b[2J\x1b[1;1HSH3 Heather room\nBuild: %s\nError: %s\nRelease all buttons\nL: "
                "retry   START: exit\n",
                SH3_BUILD_ID, reason);
    Retry session;
    MovementControls input(session, fast);
    while (session.state() != S::stopped && aptMainLoop()) {
        hidScanInput();
        input.frame(hidKeysHeld(), hidKeysDown(), svcGetSystemTick());
        gfxFlushBuffers();
        gfxSwapBuffers();
        gspWaitForVBlank();
    }
    return session.retry;
}
bool choose_mode(SkinningMode &mode, bool fast) {
    std::printf("\x1b[2J\x1b[1;1HSH3 skinning comparison\nBuild: %s\n"
                "Release all buttons first\nA: CPU reference\nL: HYBRID candidate\n"
                "START: exit\nSELECT in scene: choose again\n",
                SH3_BUILD_ID);
    Retry session(true);
    MovementControls controls(session, fast);
    while (session.state() != S::stopped && aptMainLoop()) {
        hidScanInput();
        controls.frame(hidKeysHeld(), hidKeysDown(), svcGetSystemTick());
        gfxFlushBuffers();
        gfxSwapBuffers();
        gspWaitForVBlank();
    }
    mode = session.hybrid ? SkinningMode::hybrid : SkinningMode::cpu;
    return session.retry;
}
void capture_hud(SkinningCapture &capture, unsigned page) {
    std::printf("Window: %s n=%u fail=%u\x1b[K\n", capture.complete() ? "DONE" : "idle",
                capture.count(), capture.failed());
    if (!capture.complete())
        return;
    std::printf("Frames: %llu..%llu  page %u/2\x1b[K\n",
                static_cast<unsigned long long>(capture.first()),
                static_cast<unsigned long long>(capture.last()), page + 1);
    constexpr const char *names[]{"Move/contact", "Anim/pose",   "Validate",  "Palette",
                                  "CPU deform",   "Sort/expand", "GPU rows",  "Own wait",
                                  "Copy/flush",   "Submit",      "CPU total", "Cadence",
                                  "GPU queue"};
    std::printf("ms             med     p95     max\n");
    for (unsigned i = page * 7; i < std::min(page * 7 + 7, 13U); ++i) {
        const auto m = capture.summarize(i, SYSCLOCK_ARM11);
        std::printf("%-12s %6.2f %6.2f %6.2f\x1b[K\n", names[i], m.median, m.p95, m.maximum);
        if (i == 12)
            std::printf("GPU matched: %u/256\x1b[K\n", m.count);
    }
}
} // namespace
int run_room(const char *directory, bool comparison) {
    Screens screens;
    std::unique_ptr<RoomAssets> assets;
    std::unique_ptr<SkinningCapture> capture;
    if (comparison) {
        capture.reset(new (std::nothrow) SkinningCapture);
        if (!capture) {
            std::printf("HS_CAPTURE_ALLOC\n");
            return 1;
        }
    }
    SkinningMode mode = SkinningMode::cpu;
    bool selection = comparison;
    for (;;) {
        if (selection) {
            if (!choose_mode(mode, screens.fast))
                return 0;
            selection = false;
            capture->cancel();
        }
        const auto load_start = svcGetSystemTick();
        std::printf("\x1b[2J\x1b[1;1HSH3 Heather room\nBuild: %s\nLoading checked room data...\n",
                    SH3_BUILD_ID);
        gfxFlushBuffers();
        gfxSwapBuffers();
        gspWaitForVBlank();
        const char *failure = nullptr;
        const auto loaded = read_room_runtime(directory, assets);
        if (loaded.error != ports::FileError::ok)
            failure = loaded.field;
        else {
            std::printf("Preparing graphics and textures...\n");
            gfxFlushBuffers();
            gfxSwapBuffers();
            gspWaitForVBlank();
            RoomTextures textures(directory);
            std::unique_ptr<RoomRenderer> owner(
                new (std::nothrow) RoomRenderer(assets->map, assets->rig.shared, textures, mode,
                                                comparison ? sizeof(SkinningCapture) : 0));
            if (!owner || !owner->ready())
                failure = owner ? owner->stage() : "RENDERER_ALLOC";
            else {
                auto &renderer = *owner;
                domain::InspectionLocomotionReader reader(assets->rig);
                std::unique_ptr<application::RoomLoop> app(new (std::nothrow) application::RoomLoop(
                    assets->rig.profile, domain::locomotion_rig_skeleton(assets->rig), reader,
                    assets->contacts, renderer, assets->spawn, assets->yaw));
                if (!app)
                    failure = "CONTROLLER_ALLOC";
                else {
                    domain::WorkTrace trace;
                    if (comparison) {
                        // Construction already established the same spawn and idle pose.
                        app->dispatch(domain::LifecycleEvent::toggle_pause);
                        trace.clock = [](void *) noexcept { return svcGetSystemTick(); };
                        trace.sink = [](void *context, const domain::WorkSample &sample) noexcept {
                            static_cast<SkinningCapture *>(context)->record(sample);
                        };
                        trace.context = capture.get();
                        app->trace(&trace);
                        renderer.trace(&trace);
                    }
                    unsigned page = 0;
                    // Hook dies before the loop/controller, renderer and graphics services.
                    MovementControls controls(*app, screens.fast);
                    FrameCadence cadence(SYSCLOCK_ARM11);
                    const auto load_ms =
                        double(svcGetSystemTick() - load_start) * 1000 / SYSCLOCK_ARM11;
                    std::uint64_t hud = 0, previous = 0;
                    unsigned r_presses = 0, r_steps = 0, slow = 0;
                    std::printf("\x1b[2J");
                    while (aptMainLoop() && app->state() != S::stopped) {
                        hidScanInput();
                        const auto down = hidKeysDown(), held = hidKeysHeld();
                        const auto now = svcGetSystemTick();
                        if (comparison && app->state() != S::suspended &&
                            !app->awaiting_release() && !(down & KEY_START)) {
                            if (held & down & KEY_SELECT) {
                                selection = true;
                                break;
                            }
                            if ((held & down & KEY_Y) && !capture->active()) {
                                page ^= 1;
                                std::printf("\x1b[2J");
                            }
                            if ((held & down & KEY_X) && app->state() == S::running &&
                                !(down & (KEY_A | KEY_L))) {
                                capture->start();
                                std::printf("\x1b[2J\x1b[1;1HMeasuring: 32 warmup + 256 frames\n"
                                            "No HUD refresh during window\n");
                            }
                        }
                        if (comparison && capture->active() &&
                            (app->state() != S::running || app->awaiting_release() ||
                             (down & (KEY_A | KEY_L | KEY_START))))
                            capture->cancel();
                        const double frame_ms = previous && now >= previous
                                                    ? double(now - previous) * 1000 / SYSCLOCK_ARM11
                                                    : 0;
                        previous = now;
                        if (down & KEY_R)
                            ++r_presses;
                        if (app->state() == S::running && !app->awaiting_release() &&
                            frame_ms > 120)
                            ++slow;
                        const bool was_paused = app->state() == S::paused;
                        const auto updates = controls.frame(held, down, now);
                        if (was_paused)
                            r_steps += updates;
                        if (app->state() == S::stopped)
                            break;
                        if (app->state() == S::suspended) {
                            cadence.reset();
                            previous = 0;
                            gspWaitForVBlank();
                            continue;
                        }
                        if (app->render_result() != ports::RenderResult::presented)
                            gspWaitForVBlank();
                        cadence.record(svcGetSystemTick(),
                                       app->render_result() == ports::RenderResult::presented);
                        if (comparison && capture->active())
                            continue;
                        if (hud && now >= hud && now - hud < SYSCLOCK_ARM11 / 4 && !down)
                            continue;
                        hud = now;
                        const auto &s = app->snapshot();
                        constexpr const char *faults[]{"none", "spawn validation",
                                                       "movement/animation", "graphics"};
                        if (comparison) {
                            std::printf(
                                "\x1b[1;1HSH3 HS / hp34  %s\nAsked:%s Active:%s\x1b[K\n"
                                "Status: %-24s\n%-8s %-24s\nError: %-20s\n"
                                "Step: %lu  Clip: %lu  Q12: %lu\x1b[K\n"
                                "R raw: %u  R steps: %u\x1b[K\n"
                                "A:pause R:step L:reset START:exit\n"
                                "SELECT:mode X:window Y:results page\n"
                                "CPU:%s Load:%.0f ms Mem:%.2f MiB\x1b[K\n",
                                SH3_BUILD_ID, mode == SkinningMode::cpu ? "CPU" : "HYBRID",
                                renderer.skinning_mode() == SkinningMode::cpu ? "CPU" : "HYBRID",
                                renderer.skinning_status(),
                                app->state() == S::paused ? "PAUSED" : "RUNNING",
                                app->awaiting_release() ? "Release all buttons" : "",
                                faults[unsigned(app->fault())],
                                static_cast<unsigned long>(s.movement.ordinal),
                                static_cast<unsigned long>(s.animation.clock.target_id),
                                static_cast<unsigned long>(s.animation.clock.counter), r_presses,
                                r_steps, screens.fast ? "New fast" : "default", load_ms,
                                double(renderer.accounted_bytes()) / (1024 * 1024));
                            capture_hud(*capture, page);
                            std::printf("\x1b[J");
                            continue;
                        }
                        std::printf(
                            "\x1b[1;1HSH3 - Heather / hp34\nBuild: %s\n"
                            "CAMARA FIJA PROPIA\n%s\n"
                            "D-pad: walk/turn; B: run\nA: pause; R: hold 0.2s, release\nL: "
                            "restart/retry; START: exit\n"
                            "%-8s  %-24s\nError: %-20s\nStep: %lu  Clip: %lu  Q12: %lu\x1b[K\n"
                            "Accounted: %.2f / 64 MiB\n25 fixed updates/s; max 3/frame\n"
                            "CPU: %s  Load: %.0f ms\x1b[K\nFPS submit: %.1f Frame: %.1f ms\x1b[K\n"
                            "Prep: %.1f Submit: %.1f ms\x1b[K\nGPU previous: %.1f ms\x1b[K\n"
                            "Slow frames: %u Updates: %u\x1b[K\n"
                            "Held: %08lX Down: %08lX\nR presses: %u (raw)\x1b[K\n"
                            "R steps: %u\x1b[K\n",
                            SH3_BUILD_ID,
                            assets->map.material_count ? "MATERIALES ORIGINALES / LUZ FIJA"
                                                       : "29 FORMAS: COLOR/LUZ DIAGNOSTICO",
                            app->state() == S::paused ? "PAUSED" : "RUNNING",
                            app->awaiting_release() ? "Release all buttons" : "",
                            faults[unsigned(app->fault())],
                            static_cast<unsigned long>(s.movement.ordinal),
                            static_cast<unsigned long>(s.animation.clock.target_id),
                            static_cast<unsigned long>(s.animation.clock.counter),
                            double(renderer.accounted_bytes()) / (1024 * 1024),
                            screens.fast ? "New fast" : "default", load_ms,
                            cadence.fps().value_or(0), frame_ms, renderer.prepare_ms(),
                            renderer.submit_ms(), double(C3D_GetDrawingTime()), slow, updates,
                            static_cast<unsigned long>(held), static_cast<unsigned long>(down),
                            r_presses, r_steps);
                    }
                    if (!selection)
                        return 0;
                }
            }
        }
        if (selection)
            continue;
        // GPU scope has ended; retries never overlap two graphics owners.
        if (!retry_screen(failure, screens.fast))
            return 1;
    }
}
} // namespace sh3::platform::ctr
