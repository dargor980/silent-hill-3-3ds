#include "character_renderer.hpp"
#include "sh3/application/animation_probe.hpp"
#include "sh3/platform/inspection_animation.hpp"
#include "sh3/platform/inspection_character.hpp"
#include "sh3/platform/inspection_character_lighting.hpp"
#include "sh3/platform/inspection_character_world.hpp"
#include <cstdio>
#include <memory>
#include <new>

namespace {
#if defined(SH3_CHARACTER_WORLD)
constexpr bool textured = true, captured_lighting = false;
#define CHARACTER_FOLDER "sdmc:/3ds/sh3_character_world_probe/"
#elif defined(SH3_CHARACTER_LIGHTING)
constexpr bool textured = true, captured_lighting = true;
#define CHARACTER_FOLDER "sdmc:/3ds/sh3_character_lighting_probe/"
#elif defined(SH3_CHARACTER_MATERIAL)
constexpr bool textured = true, captured_lighting = false;
#define CHARACTER_FOLDER "sdmc:/3ds/sh3_character_material_probe/"
#else
constexpr bool textured = false, captured_lighting = false;
#define CHARACTER_FOLDER "sdmc:/3ds/sh3_character_probe/"
#endif
#ifdef SH3_CHARACTER_WORLD
constexpr bool world_placement = true;
#else
constexpr bool world_placement = false;
#endif
constexpr std::size_t instance_count = world_placement ? 3 : 1;

class CharacterPresenter final : public sh3::ports::IPoseScene {
  public:
    CharacterPresenter(sh3::platform::ctr::CharacterRenderer &renderer,
                       const sh3::domain::CharacterModel &model,
                       const sh3::domain::CharacterLighting *lighting,
                       const sh3::domain::CharacterWorld *world)
        : renderer_(renderer), model_(model), lighting_(lighting), world_(world) {}
    void toggle_light() noexcept { neutral_ = !neutral_; }
    bool neutral() const noexcept { return neutral_; }
    sh3::ports::RenderResult present_pose(const sh3::domain::OrbitCamera &camera,
                                          const sh3::domain::SkeletonPose &pose) noexcept override {
        const auto begin = svcGetSystemTick();
        const bool valid = sh3::domain::character_draw(
            model_, pose, scratch_.data(), scratch_.size(), draw_.data(), draw_.size(), textured);
        skin_ms = double(svcGetSystemTick() - begin) * 1000 / SYSCLOCK_ARM11;
        if (!valid)
            return sh3::ports::RenderResult::unavailable;
        const auto lighting_begin = svcGetSystemTick();
        const bool lit =
            (!lighting_ || neutral_ ||
             sh3::domain::light_character(*lighting_, model_, scratch_.data(), scratch_.size(),
                                          colors_.data(), colors_.size(), draw_.data(),
                                          draw_.size())) &&
            (!world_ || sh3::domain::place_character(
                            *world_, model_, scratch_.data(), scratch_.size(), positions_.data(),
                            positions_.size(), draw_.data(), draw_.size()));
        light_ms = double(svcGetSystemTick() - lighting_begin) * 1000 / SYSCLOCK_ARM11;
        if (!lit)
            return sh3::ports::RenderResult::unavailable;
        const auto submitted = svcGetSystemTick();
        const auto result =
            renderer_.present(camera, draw_.data(), model_.index_count * instance_count);
        submit_ms = double(svcGetSystemTick() - submitted) * 1000 / SYSCLOCK_ARM11;
        return result;
    }
    double skin_ms{}, light_ms{}, submit_ms{};

  private:
    sh3::platform::ctr::CharacterRenderer &renderer_;
    const sh3::domain::CharacterModel &model_;
    const sh3::domain::CharacterLighting *lighting_;
    const sh3::domain::CharacterWorld *world_;
    bool neutral_{false};
    std::array<sh3::domain::LightVector,
               captured_lighting ? sh3::domain::character_vertex_limit : 0>
        colors_{};
    std::array<sh3::domain::DeformedVertex, sh3::domain::character_vertex_limit> scratch_{};
    std::array<sh3::domain::WorldPosition,
               world_placement ? sh3::domain::character_vertex_limit : 0>
        positions_{};
    std::array<sh3::domain::CharacterDrawVertex,
               sh3::domain::character_index_limit * instance_count>
        draw_{};
};
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
    std::printf("\x1b[2J\x1b[1;1HCharacter failed: %s\nBuild: %s\n\n" CHARACTER_FOLDER
                "\nCheck viewer data files.\nSTART: exit\n",
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
    std::uint32_t clip_crc{};
    const auto loaded = sh3::platform::read_inspection_animation(
        CHARACTER_FOLDER "animation.san", clip, sh3::platform::system_stdio, &clip_crc);
    if (loaded != sh3::ports::FileError::ok) {
        error(sh3::platform::file_error_name(loaded));
        return 1;
    }
    static sh3::domain::CharacterModel model;
    std::uint32_t model_crc{};
    const auto model_loaded = sh3::platform::read_inspection_character(
        CHARACTER_FOLDER "character.scm", model, sh3::platform::system_stdio, &model_crc);
    if (model_loaded != sh3::ports::FileError::ok) {
        error(sh3::platform::file_error_name(model_loaded));
        return 1;
    }
    std::unique_ptr<sh3::platform::CharacterMaterialData> material;
    std::uint32_t material_crc{};
    if constexpr (textured) {
        material.reset(new (std::nothrow) sh3::platform::CharacterMaterialData);
        if (!material) {
            error("MATERIAL_MEMORY");
            return 1;
        }
        const auto loaded_material = sh3::platform::read_character_material(
            CHARACTER_FOLDER "character.sct", *material, model_crc, model.index_count,
            sh3::platform::system_stdio, &material_crc);
        if (loaded_material != sh3::ports::FileError::ok) {
            error(sh3::platform::file_error_name(loaded_material));
            return 1;
        }
    }
    sh3::domain::CharacterLighting lighting{};
    if constexpr (captured_lighting) {
        const auto result = sh3::platform::read_character_lighting(
            CHARACTER_FOLDER "character.scl", lighting, model, model_crc, clip_crc, material_crc);
        if (result != sh3::ports::FileError::ok) {
            error(sh3::platform::file_error_name(result));
            return 1;
        }
    }
    sh3::domain::CharacterWorld world{};
    if constexpr (world_placement) {
        const auto result = sh3::platform::read_character_world(
            CHARACTER_FOLDER "character.scw", world, model, model_crc, clip_crc, material_crc);
        if (result != sh3::ports::FileError::ok) {
            error(sh3::platform::file_error_name(result));
            return 1;
        }
    }
    const char *failure = nullptr;
    {
        sh3::platform::ctr::CharacterRenderer renderer(model.index_count, material.get(),
                                                       instance_count);
        material.reset(); // GPU owns its copies; release the 3 MiB staging allocation.
        if (!renderer.ready())
            failure = renderer.stage();
        else {
            static CharacterPresenter presenter(renderer, model,
                                                captured_lighting ? &lighting : nullptr,
                                                world_placement ? &world : nullptr);
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
                if constexpr (captured_lighting) {
                    if ((down & KEY_SELECT) && !(down & KEY_START) &&
                        app.view().state() == sh3::domain::SessionState::running &&
                        !app.view().awaiting_release())
                        presenter.toggle_light();
                }
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
                std::printf(
                    "\x1b[1;1HSH3 - %s\nBuild: %s\n"
                    "Clip 0x1449 / 3 bones / 24 samples\n"
                    "%-40s\n"
                    "%lu vertices / %lu triangles\n\n"
                    "A: pause  R: step when paused\nL: restart clip\n"
                    "D-pad: camera  X/Y: zoom\nB: camera reset  START: exit\n%s\n"
                    "%-8s Q12: %-6lu Sample: %2lu\n%-36s\n"
                    "Camera: %4.2f %4.2f %4.2f\n"
                    "Preview clock: 25 evaluations/s\n"
                    "Skin CPU: %6.2f ms\n%s CPU: %6.2f ms\nSubmit+wait: %6.2f ms\nGPU "
                    "previous: %6.2f ms\n"
                    "%s\n",
                    world_placement ? "world placement" : "animated mesh inspection", SH3_BUILD_ID,
                    captured_lighting && !presenter.neutral()
                        ? "Captured lights / fixed / two-sided"
                    : world_placement ? "3 fixed placements / neutral light"
                    : textured        ? "3 textures / neutral light / two-sided"
                                      : "Own inspection shading / two-sided",
                    static_cast<unsigned long>(model.vertex_count * instance_count),
                    static_cast<unsigned long>(model.index_count / 3 * instance_count),
                    captured_lighting ? "SELECT: captured / neutral light"
                    : world_placement ? "Shared clip / fixed world transforms"
                                      : "",
                    app.paused() ? "PAUSED" : "PLAYING", static_cast<unsigned long>(app.counter()),
                    static_cast<unsigned long>(app.counter() / 4096),
                    view.awaiting_release() ? "Release all controls" : "Animation ready",
                    double(view.camera().yaw), double(view.camera().elevation),
                    double(view.camera().distance), presenter.skin_ms,
                    world_placement ? "Place" : "Light", presenter.light_ms, presenter.submit_ms,
                    double(C3D_GetDrawingTime()),
                    (captured_lighting || world_placement) ? "Scene lights / damage / death pending"
                    : textured                             ? "PS2 lighting / damage / death pending"
                                                           : "Materials / damage / death pending");
            }
        }
    }
    if (failure) {
        error(failure);
        return 1;
    }
    return 0;
}
