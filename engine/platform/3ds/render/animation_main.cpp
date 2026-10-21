#include "renderer.hpp"
#include "sh3/application/animation_probe.hpp"
#include "sh3/application/skeleton_presenter.hpp"
#include "sh3/platform/inspection_animation.hpp"
#include <cstdio>

namespace {
class Screens final {
  public:
    Screens() {
        gfxInitDefault();
        consoleInit(GFX_BOTTOM, nullptr);
    }
    ~Screens() { gfxExit(); }
    Screens(const Screens &) = delete;
    Screens &operator=(const Screens &) = delete;
};
class Hook final {
  public:
    explicit Hook(sh3::application::AnimationProbe &app) : app_(app) {
        aptHook(&cookie_, callback, this);
    }
    ~Hook() { aptUnhook(&cookie_); }
    Hook(const Hook &) = delete;
    Hook &operator=(const Hook &) = delete;

  private:
    static void callback(APT_HookType type, void *context) {
        auto &app = static_cast<Hook *>(context)->app_;
        using E = sh3::domain::LifecycleEvent;
        if (type == APTHOOK_ONSUSPEND || type == APTHOOK_ONSLEEP)
            app.dispatch(E::suspend);
        else if (type == APTHOOK_ONRESTORE || type == APTHOOK_ONWAKEUP)
            app.dispatch(E::resume);
        else if (type == APTHOOK_ONEXIT)
            app.dispatch(E::quit);
    }
    sh3::application::AnimationProbe &app_;
    aptHookCookie cookie_{};
};
void error(const char *stage) {
    std::printf("\x1b[2J\x1b[1;1HAnimation failed: %s\nBuild: %s\n\n"
                "/3ds/sh3_animation_probe/animation.san\n\nSTART: exit\n",
                stage, SH3_BUILD_ID);
    while (aptMainLoop()) {
        hidScanInput();
        if (hidKeysDown() & KEY_START)
            break;
        gfxFlushBuffers();
        gfxSwapBuffers();
        gspWaitForVBlank();
    }
}
} // namespace
int main() {
    Screens screens;
    sh3::domain::InspectionClip clip{};
    const auto loaded = sh3::platform::read_inspection_animation(
        "sdmc:/3ds/sh3_animation_probe/animation.san", clip);
    if (loaded != sh3::ports::FileError::ok) {
        error(sh3::platform::file_error_name(loaded));
        return 1;
    }
    const char *failure = nullptr;
    {
        const auto mesh = sh3::domain::skeleton_mesh(clip, sh3::domain::evaluate_pose(clip, 0));
        sh3::platform::ctr::SceneRenderer renderer(
            sh3::platform::InspectionMesh{mesh.data(), mesh.size()});
        if (!renderer.ready())
            failure = renderer.stage();
        else {
            sh3::application::SkeletonPresenter presenter(renderer, clip);
            sh3::application::AnimationProbe app(presenter, clip);
            Hook hook(app);
            auto previous = svcGetSystemTick();
            while (aptMainLoop() && app.view().state() != sh3::domain::SessionState::stopped) {
                const auto now = svcGetSystemTick();
                const auto seconds = static_cast<float>(now - previous) / SYSCLOCK_ARM11;
                previous = now;
                if (app.view().state() == sh3::domain::SessionState::suspended) {
                    gspWaitForVBlank();
                    continue;
                }
                hidScanInput();
                const auto held = hidKeysHeld(), down = hidKeysDown();
                const sh3::application::CameraInput camera{
                    float(bool(held & KEY_DRIGHT)) - float(bool(held & KEY_DLEFT)),
                    float(bool(held & KEY_DUP)) - float(bool(held & KEY_DDOWN)),
                    float(bool(held & KEY_Y)) - float(bool(held & KEY_X)),
                    bool(down & KEY_B),
                    bool(down & KEY_START),
                    bool(held | down)};
                app.step(camera, {bool(down & KEY_A), bool(down & KEY_R), bool(down & KEY_L)},
                         seconds);
                const auto &view = app.view();
                if (view.state() == sh3::domain::SessionState::stopped) {
                    if (view.result() == sh3::ports::RenderResult::unavailable ||
                        view.result() == sh3::ports::RenderResult::invalid_camera)
                        failure = "PRESENT";
                    break;
                }
                if (view.result() != sh3::ports::RenderResult::presented)
                    gspWaitForVBlank();
                std::printf("\x1b[1;1HSH3 - animation inspection\nBuild: %s\n"
                            "Clip 0x1449 / 3 bones / 24 samples\n"
                            "Axes RGB = XYZ; gray = parent link\n\n"
                            "A: pause  R: step when paused\nL: restart clip\n"
                            "D-pad: camera  X/Y: zoom\nB: camera reset  START: exit\n\n"
                            "%-8s Q12: %-6lu Sample: %2lu\n%-36s\n"
                            "Camera: %4.2f %4.2f %4.2f\n"
                            "Preview clock: 25 evaluations/s\n"
                            "Damage / death: PENDING\nHorse mesh / skinning: PENDING\n",
                            SH3_BUILD_ID, app.paused() ? "PAUSED" : "PLAYING",
                            static_cast<unsigned long>(app.counter()),
                            static_cast<unsigned long>(app.counter() / 4096),
                            view.awaiting_release() ? "Release all controls" : "Animation ready",
                            double(view.camera().yaw), double(view.camera().elevation),
                            double(view.camera().distance));
            }
        }
    }
    if (failure) {
        error(failure);
        return 1;
    }
    return 0;
}
