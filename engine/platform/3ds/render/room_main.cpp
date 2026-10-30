#include "room_main.hpp"
#include "../movement_controls.hpp"
#include "room_renderer.hpp"
#include "sh3/application/room_loop.hpp"
#include "sh3/platform/frame_cadence.hpp"
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
    unsigned step(application::MovementInput input, std::uint64_t) noexcept override {
        if (input.quit)
            lifecycle.apply(domain::LifecycleEvent::quit);
        if (state() == S::suspended || state() == S::stopped)
            return 0;
        if (release)
            release = input.any_held;
        else if (input.restart) {
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
    bool release{true}, retry{};
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
} // namespace
int run_room(const char *directory) {
    Screens screens;
    std::unique_ptr<RoomAssets> assets;
    for (;;) {
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
            RoomRenderer renderer(assets->map, assets->rig.shared, textures);
            if (!renderer.ready())
                failure = renderer.stage();
            else {
                domain::InspectionLocomotionReader reader(assets->rig);
                std::unique_ptr<application::RoomLoop> app(new (std::nothrow) application::RoomLoop(
                    assets->rig.profile, domain::locomotion_rig_skeleton(assets->rig), reader,
                    assets->contacts, renderer, assets->spawn, assets->yaw));
                if (!app)
                    failure = "CONTROLLER_ALLOC";
                else {
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
                        if (hud && now >= hud && now - hud < SYSCLOCK_ARM11 / 4 && !down)
                            continue;
                        hud = now;
                        const auto &s = app->snapshot();
                        constexpr const char *faults[]{"none", "spawn validation",
                                                       "movement/animation", "graphics"};
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
                    return 0;
                }
            }
        }
        // GPU scope has ended; retries never overlap two graphics owners.
        if (!retry_screen(failure, screens.fast))
            return 1;
    }
}
} // namespace sh3::platform::ctr
