#include "rig_renderer.hpp"
#include "sh3/application/locomotion_probe.hpp"
#include "sh3/platform/frame_cadence.hpp"
#include "sh3/platform/inspection_locomotion.hpp"
#include <cstdio>

namespace {
constexpr const char *folder = "sdmc:/3ds/sh3_heather_probe/";
void step_controls(sh3::application::LocomotionProbe &app, u32 held, u32 down, float seconds) {
    app.step({float(bool(held & KEY_DRIGHT)) - float(bool(held & KEY_DLEFT)),
              float(bool(held & KEY_DUP)) - float(bool(held & KEY_DDOWN)),
              float(bool(held & KEY_Y)) - float(bool(held & KEY_X)), bool(down & KEY_B),
              bool(down & KEY_START), bool(held | down)},
             {bool(down & KEY_A), bool(down & KEY_R), bool(down & KEY_L),
              bool(down & KEY_ZL), bool(down & KEY_ZR)}, seconds, bool(down & KEY_SELECT));
}
class Textures final : public sh3::ports::IRigTextures {
  public:
    bool read(const sh3::domain::RigMaterial &m, std::uint8_t *out,
              std::size_t bytes) noexcept override {
        char path[96];
        std::snprintf(path, sizeof(path), "%stexture-%02lu.rgba", folder,
                      static_cast<unsigned long>(m.texture));
        return sh3::platform::read_rig_texture(path, m, out, bytes) == sh3::ports::FileError::ok;
    }
};
class Presenter final : public sh3::ports::IRigScene {
  public:
    Presenter(sh3::platform::ctr::RigRenderer &renderer, const sh3::domain::InspectionRig &model)
        : renderer_(renderer), model_(model) {}
    sh3::ports::RenderResult present_pose(const sh3::domain::OrbitCamera &camera,
                                          const sh3::domain::RigPose &pose) noexcept override {
        const auto begin = svcGetSystemTick();
        const auto valid =
            sh3::domain::rig_draw(model_, pose, camera, palette_, order_, scratch_.data(),
                                  scratch_.size(), draw_.data(), draw_.size());
        skin_ms = double(svcGetSystemTick() - begin) * 1000 / SYSCLOCK_ARM11;
        if (!valid)
            return sh3::ports::RenderResult::unavailable;
        const auto submitted = svcGetSystemTick();
        const auto result = renderer_.present(camera, draw_.data(), model_.index_count);
        submit_ms = double(svcGetSystemTick() - submitted) * 1000 / SYSCLOCK_ARM11;
        return result;
    }
    double skin_ms{}, submit_ms{};

  private:
    sh3::platform::ctr::RigRenderer &renderer_;
    const sh3::domain::InspectionRig &model_;
    sh3::domain::RigPalette palette_{};
    sh3::domain::RigSortOrder order_{};
    std::array<sh3::domain::RigVertexScratch, sh3::domain::rig_vertices> scratch_{};
    std::array<sh3::domain::CharacterDrawVertex, sh3::domain::rig_indices> draw_{};
};
class Screens final {
  public:
    Screens() {
        gfxInitDefault();
        consoleInit(GFX_BOTTOM, nullptr);
        bool is_new = false;
        fast_ = R_SUCCEEDED(APT_CheckNew3DS(&is_new)) && is_new;
        if (fast_)
            osSetSpeedupEnable(true);
    }
    ~Screens() {
        if (fast_)
            osSetSpeedupEnable(false);
        gfxExit();
    }
    bool fast_requested() const noexcept { return fast_; }

  private:
    bool fast_{};
};
class Hook final {
  public:
    Hook(sh3::application::LocomotionProbe &app, sh3::platform::FrameCadence &cadence, bool fast)
        : app_(app), cadence_(cadence), fast_(fast) {
        aptHook(&cookie_, callback, this);
    }
    ~Hook() { aptUnhook(&cookie_); }
    Hook(const Hook &) = delete;
    Hook &operator=(const Hook &) = delete;

  private:
    static void callback(APT_HookType type, void *context) {
        auto &self = *static_cast<Hook *>(context);
        auto &app = self.app_;
        using E = sh3::domain::LifecycleEvent;
        if (type == APTHOOK_ONSUSPEND || type == APTHOOK_ONSLEEP) {
            self.cadence_.reset();
            app.dispatch(E::suspend);
        } else if (type == APTHOOK_ONRESTORE || type == APTHOOK_ONWAKEUP) {
            self.cadence_.reset();
            if (self.fast_)
                osSetSpeedupEnable(true);
            app.dispatch(E::resume);
        } else if (type == APTHOOK_ONEXIT)
            app.dispatch(E::quit);
    }
    sh3::application::LocomotionProbe &app_;
    sh3::platform::FrameCadence &cadence_;
    bool fast_{};
    aptHookCookie cookie_{};
};
void error(const char *stage) {
    std::printf("\x1b[2J\x1b[1;1HHeather failed: %s\nBuild: %s\n\nCheck %s\nSTART: exit\n", stage,
                SH3_BUILD_ID, folder);
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
    static sh3::domain::InspectionLocomotion bundle;
    const auto loaded = sh3::platform::read_locomotion_bundle(folder, bundle);
    if (loaded.error != sh3::ports::FileError::ok) {
        error(loaded.field);
        return 1;
    }
    const auto &model = bundle.shared;
    const char *failure = nullptr;
    {
        Textures textures;
        sh3::platform::ctr::RigRenderer renderer(model, textures);
        if (!renderer.ready())
            failure = renderer.stage();
        else {
            static Presenter presenter(renderer, model);
            static const sh3::domain::InspectionLocomotionReader reader(bundle);
            static sh3::application::LocomotionProbe app(
                presenter, bundle.profile, sh3::domain::locomotion_rig_skeleton(bundle), reader);
            sh3::platform::FrameCadence cadence(SYSCLOCK_ARM11);
            Hook hook(app, cadence, screens.fast_requested());
            auto previous = svcGetSystemTick();
            std::uint64_t last_hud = 0;
            while (aptMainLoop() && app.view().state() != sh3::domain::SessionState::stopped) {
                const auto now = svcGetSystemTick();
                const auto seconds = static_cast<float>(double(now - previous) / SYSCLOCK_ARM11);
                previous = now;
                if (app.view().state() == sh3::domain::SessionState::suspended) {
                    gspWaitForVBlank();
                    continue;
                }
                hidScanInput();
                const auto held = hidKeysHeld(), down = hidKeysDown();
                step_controls(app, held, down, seconds);
                const auto &view = app.view();
                if (view.state() == sh3::domain::SessionState::stopped) {
                    if (view.result() == sh3::ports::RenderResult::unavailable ||
                        view.result() == sh3::ports::RenderResult::invalid_camera)
                        failure = app.ready() ? "PRESENT" : app.notice_text();
                    break;
                }
                if (view.result() != sh3::ports::RenderResult::presented)
                    gspWaitForVBlank();
                const auto completed = svcGetSystemTick();
                cadence.record(completed, view.result() == sh3::ports::RenderResult::presented);
                // Text is diagnostic; avoid rewriting the entire bottom framebuffer each draw.
                if (last_hud && completed - last_hud < SYSCLOCK_ARM11 / 4 && !down)
                    continue;
                last_hud = completed;
                char fps[20];
                if (cadence.fps())
                    std::snprintf(fps, sizeof(fps), "%5.1f", *cadence.fps());
                else
                    std::snprintf(fps, sizeof(fps), " --.-");
                const auto &clock = app.snapshot().clock;
                std::printf("\x1b[1;1HSH3 - Heather locomotion\nBuild: %s\n"
                            "Clips 101/109/113 / %lu bones\n"
                            "%lu vertices / %lu triangles\n%lu textures / neutral light\n"
                            "\nZL/ZR: previous/next clip\n"
                            "A: pause  R: step  L: restart\nSELECT: body/face  X/Y: zoom\nD-pad: "
                            "camera  B: reset  "
                            "START: exit\n\n"
                            "%-8s Q12: %-6lu\n"
                            "%3lu -> %3lu Mode: %lu Blend: %4lu\n%-39s\n"
                            "View: %-4s Distance: %.2f\nFPS submit: %s  CPU: %-8s\nSkin+sort CPU: "
                            "%6.2f ms\n"
                            "Submit+wait: %6.2f ms\nGPU previous: %6.2f ms\n"
                            "25 updates/s; ticks=2; in place\n",
                            SH3_BUILD_ID,
                            static_cast<unsigned long>(model.bone_count),
                            static_cast<unsigned long>(model.vertex_count),
                            static_cast<unsigned long>(model.index_count / 3),
                            static_cast<unsigned long>(model.material_count),
                            app.paused() ? "PAUSED" : "PLAYING",
                            static_cast<unsigned long>(clock.counter),
                            static_cast<unsigned long>(clock.source_id),
                            static_cast<unsigned long>(clock.target_id),
                            static_cast<unsigned long>(clock.mode),
                            static_cast<unsigned long>(clock.blend),
                            view.awaiting_release() ? "Release all controls" : app.notice_text(),
                            app.face_view() ? "FACE" : "BODY", double(view.camera().distance),
                            fps, screens.fast_requested() ? "New fast" : "default",
                            presenter.skin_ms, presenter.submit_ms, double(C3D_GetDrawingTime()));
            }
        }
    }
    if (failure) {
        error(failure);
        return 1;
    }
    return 0;
}
