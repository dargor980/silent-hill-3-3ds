#include "renderer.hpp"
#include "sh3/application/render_probe.hpp"
#include <cstdio>
#include <memory>
#include <new>

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
    explicit Hook(sh3::application::RenderProbe &app) : app_(app) {
        aptHook(&cookie_, callback, this);
    }
    ~Hook() { aptUnhook(&cookie_); }
    Hook(const Hook &) = delete;
    Hook &operator=(const Hook &) = delete;

  private:
    static void callback(APT_HookType type, void *context) {
        using E = sh3::domain::LifecycleEvent;
        auto &app = static_cast<Hook *>(context)->app_;
        if (type == APTHOOK_ONSUSPEND || type == APTHOOK_ONSLEEP) {
            app.dispatch(E::suspend);
        } else if (type == APTHOOK_ONRESTORE || type == APTHOOK_ONWAKEUP) {
            app.dispatch(E::resume);
        } else if (type == APTHOOK_ONEXIT) {
            app.dispatch(E::quit);
        }
    }
    sh3::application::RenderProbe &app_;
    aptHookCookie cookie_{};
};
void show_error(const char *stage) {
    std::printf("\x1b[2J\x1b[1;1HRender probe failed: %s\nBuild: %s\nSTART: exit\n", stage,
                SH3_BUILD_ID);
#ifdef SH3_TEXTURE_INSPECTION
    std::printf("\nSD file:\n/3ds/sh3_texture_probe/texture.stx\n");
#elif defined(SH3_GEOMETRY_INSPECTION)
    std::printf("\nSD file:\n/3ds/sh3_geometry_probe/geometry.sgm\n");
#elif defined(SH3_MATERIAL_INSPECTION)
    std::printf("\nSD folder:\n/3ds/sh3_material_probe/\ngeometry.sgm + texture.stx\n");
#endif
    while (aptMainLoop()) {
        hidScanInput();
        if (hidKeysDown() & KEY_START) {
            break;
        }
        gfxFlushBuffers();
        gfxSwapBuffers();
        gspWaitForVBlank();
    }
}
} // namespace

int main() {
    Screens screens;
#if defined(SH3_TEXTURE_INSPECTION) || defined(SH3_MATERIAL_INSPECTION)
    auto pixels = std::unique_ptr<std::uint8_t[]>(
        new (std::nothrow) std::uint8_t[sh3::platform::inspection_bytes]);
    if (!pixels) {
        show_error("TEXTURE_MEMORY");
        return 1;
    }
    const auto texture_loaded = sh3::platform::read_inspection_texture(
#ifdef SH3_MATERIAL_INSPECTION
        "sdmc:/3ds/sh3_material_probe/texture.stx", pixels.get(), sh3::platform::inspection_bytes);
#else
        "sdmc:/3ds/sh3_texture_probe/texture.stx", pixels.get(), sh3::platform::inspection_bytes);
#endif
    if (texture_loaded != sh3::ports::FileError::ok) {
        show_error(sh3::platform::file_error_name(texture_loaded));
        return 1;
    }
#endif
#ifdef SH3_TEXTURE_INSPECTION
    constexpr const char *heading = "SH3 - private texture inspection";
    constexpr const char *description = "SD texture 256x256 / own panel";
    constexpr const char *limits = "Opaque RGB; material unverified";
#endif
#if defined(SH3_GEOMETRY_INSPECTION) || defined(SH3_MATERIAL_INSPECTION)
    auto vertices = std::unique_ptr<sh3::domain::SceneVertex[]>(
        new (std::nothrow) sh3::domain::SceneVertex[sh3::platform::inspection_max_vertices]);
    if (!vertices) {
        show_error("GEOMETRY_MEMORY");
        return 1;
    }
    std::size_t vertex_count = 0;
    const auto loaded = sh3::platform::read_inspection_geometry(
#ifdef SH3_MATERIAL_INSPECTION
        "sdmc:/3ds/sh3_material_probe/geometry.sgm", vertices.get(),
#else
        "sdmc:/3ds/sh3_geometry_probe/geometry.sgm", vertices.get(),
#endif
        sh3::platform::inspection_max_vertices, vertex_count);
    if (loaded != sh3::ports::FileError::ok) {
        show_error(sh3::platform::file_error_name(loaded));
        return 1;
    }
#ifdef SH3_MATERIAL_INSPECTION
    constexpr const char *heading = "SH3 - material inspection";
    constexpr const char *description = "Glass panels / checker backdrop";
    constexpr const char *limits = "Inspection view; captured light/fog";
#else
    constexpr const char *heading = "SH3 - geometry inspection";
    constexpr const char *description = "SD mesh / diagnostic checker";
    constexpr const char *limits = "Inspection scale; own material";
#endif
#elif !defined(SH3_TEXTURE_INSPECTION)
    constexpr const char *heading = "SH3 - synthetic 3D probe";
    constexpr const char *description = "Own geometry; no game data";
    constexpr const char *limits = "Physical 2DS XL: NOT VERIFIED";
#endif
    // Scope ensures Citro3D is fully stopped before the error console uses gfx directly.
    const char *failure = nullptr;
    {
#ifdef SH3_MATERIAL_INSPECTION
        sh3::platform::ctr::SceneRenderer renderer(
            sh3::platform::InspectionMesh{vertices.get(), vertex_count},
            sh3::platform::InspectionPixels{pixels.get(), sh3::platform::inspection_bytes});
        vertices.reset();
        pixels.reset();
#elif defined(SH3_TEXTURE_INSPECTION)
        sh3::platform::ctr::SceneRenderer renderer(
            sh3::platform::InspectionPixels{pixels.get(), sh3::platform::inspection_bytes});
        pixels.reset();
#elif defined(SH3_GEOMETRY_INSPECTION)
        sh3::platform::ctr::SceneRenderer renderer(
            sh3::platform::InspectionMesh{vertices.get(), vertex_count});
        vertices.reset();
#else
        sh3::platform::ctr::SceneRenderer renderer;
#endif
        if (!renderer.ready()) {
            failure = renderer.stage();
        } else {
            sh3::application::RenderProbe app(renderer);
            Hook hook(app);
            auto previous = svcGetSystemTick();
            unsigned long frames = 0;
            while (aptMainLoop() && app.state() != sh3::domain::SessionState::stopped) {
                const auto now = svcGetSystemTick();
                const auto seconds = static_cast<float>(now - previous) / SYSCLOCK_ARM11;
                previous = now;
                if (app.state() == sh3::domain::SessionState::suspended) {
                    gspWaitForVBlank();
                    continue;
                }
                hidScanInput();
                const auto held = hidKeysHeld();
                const auto down = hidKeysDown();
                const sh3::application::CameraInput input{
                    float(bool(held & KEY_DRIGHT)) - float(bool(held & KEY_DLEFT)),
                    float(bool(held & KEY_DUP)) - float(bool(held & KEY_DDOWN)),
                    float(bool(held & KEY_Y)) - float(bool(held & KEY_X)),
                    bool(down & KEY_B),
                    bool(down & KEY_START),
                    bool(held | down)};
                app.step(input, seconds);
                if (app.state() == sh3::domain::SessionState::stopped) {
                    if (app.result() == sh3::ports::RenderResult::unavailable ||
                        app.result() == sh3::ports::RenderResult::invalid_camera) {
                        failure = "PRESENT";
                    }
                    break;
                }
                if (app.result() == sh3::ports::RenderResult::presented) {
                    ++frames;
                } else {
                    gspWaitForVBlank();
                }
                const auto &camera = app.camera();
                std::printf(
                    "\x1b[1;1H%s\nBuild: %s\n"
                    "%s\n\n"
                    "D-pad: orbit / elevation\nX/Y: zoom in / out\nB: reset  START: exit\n\n"
                    "Camera: %5.2f %5.2f %5.2f\nFrames: %-10lu\n%-36s\n"
                    "%s\n",
                    heading, SH3_BUILD_ID, description, double(camera.yaw),
                    double(camera.elevation), double(camera.distance), frames,
                    app.awaiting_release() ? "Release all controls" : "Camera ready", limits);
            }
        }
    }
    if (failure) {
        show_error(failure);
        return 1;
    }
    return 0;
}
