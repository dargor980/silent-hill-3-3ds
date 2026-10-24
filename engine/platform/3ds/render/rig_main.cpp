#include "rig_renderer.hpp"
#include "sh3/application/rig_probe.hpp"
#include <cstdio>

namespace {
constexpr const char *folder = "sdmc:/3ds/sh3_heather_probe/";
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
    std::array<sh3::domain::DeformedVertex, sh3::domain::rig_vertices> scratch_{};
    std::array<sh3::domain::CharacterDrawVertex, sh3::domain::rig_indices> draw_{};
};
class Screens final {
  public:
    Screens() {
        gfxInitDefault();
        consoleInit(GFX_BOTTOM, nullptr);
    }
    ~Screens() { gfxExit(); }
};
class Hook final {
  public:
    explicit Hook(sh3::application::RigProbe &app) : app_(app) {
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
    sh3::application::RigProbe &app_;
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
    static sh3::domain::InspectionRig model;
    const auto loaded =
        sh3::platform::read_inspection_rig("sdmc:/3ds/sh3_heather_probe/heather.sri", model);
    if (loaded != sh3::ports::FileError::ok) {
        error(sh3::platform::file_error_name(loaded));
        return 1;
    }
    const char *failure = nullptr;
    {
        Textures textures;
        sh3::platform::ctr::RigRenderer renderer(model, textures);
        if (!renderer.ready())
            failure = renderer.stage();
        else {
            static Presenter presenter(renderer, model);
            sh3::application::RigProbe app(presenter, model);
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
                app.step({float(bool(held & KEY_DRIGHT)) - float(bool(held & KEY_DLEFT)),
                          float(bool(held & KEY_DUP)) - float(bool(held & KEY_DDOWN)),
                          float(bool(held & KEY_Y)) - float(bool(held & KEY_X)), bool(down & KEY_B),
                          bool(down & KEY_START), bool(held | down)},
                         {bool(down & KEY_A), bool(down & KEY_R), bool(down & KEY_L)}, seconds,
                         bool(down & KEY_SELECT));
                const auto &view = app.view();
                if (view.state() == sh3::domain::SessionState::stopped) {
                    if (view.result() == sh3::ports::RenderResult::unavailable ||
                        view.result() == sh3::ports::RenderResult::invalid_camera)
                        failure = "PRESENT";
                    break;
                }
                if (view.result() != sh3::ports::RenderResult::presented)
                    gspWaitForVBlank();
                std::printf("\x1b[1;1HSH3 - Heather original\nBuild: %s\n"
                            "Clip 0x%lx / %lu bones / %lu samples\n"
                            "%lu vertices / %lu triangles\n%lu textures / neutral light\n"
                            "\nA: pause  R: step  L: restart\nSELECT: body/face  X/Y: zoom\nD-pad: "
                            "camera  B: reset  "
                            "START: exit\n\n"
                            "%-8s Q12: %-6lu Sample: %2lu\n%-36s\n"
                            "View: %-4s Distance: %.2f\nPreview: 25 evaluations/s\nSkin+sort CPU: "
                            "%6.2f ms\n"
                            "Submit+wait: %6.2f ms\nGPU previous: %6.2f ms\n"
                            "Native timing / expressions pending\n",
                            SH3_BUILD_ID, static_cast<unsigned long>(model.clip_id),
                            static_cast<unsigned long>(model.bone_count),
                            static_cast<unsigned long>(model.sample_count),
                            static_cast<unsigned long>(model.vertex_count),
                            static_cast<unsigned long>(model.index_count / 3),
                            static_cast<unsigned long>(model.material_count),
                            app.paused() ? "PAUSED" : "PLAYING",
                            static_cast<unsigned long>(app.counter()),
                            static_cast<unsigned long>(app.counter() / 4096),
                            view.awaiting_release() ? "Release all controls" : "Animation ready",
                            app.face_view() ? "FACE" : "BODY", double(view.camera().distance),
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
