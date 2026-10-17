#include "sdk.hpp"
#include "check.hpp"
#include "tone.hpp"

namespace {
ctr_test::Sdk state;
C3D_RenderTarget screen_target;
PrintConsole screen_console;
} // namespace

namespace ctr_test {
Sdk &sdk() { return state; }
} // namespace ctr_test

void gfxInitDefault() {
    CHECK(!state.gfx);
    state.gfx = true;
    state.resources.emplace_back("gfx.init");
}
void gfxExit() {
    CHECK(state.gfx && !state.c3d && !state.c2d && !state.tone && !state.callback);
    state.gfx = false;
    state.resources.emplace_back("gfx.exit");
}
PrintConsole *consoleInit(gfxScreen_t screen, PrintConsole *console) {
    CHECK(state.gfx && screen == GFX_BOTTOM && console == nullptr);
    state.resources.emplace_back("console.init");
    return &screen_console;
}
void consoleClear() {
    CHECK(state.gfx);
    ++state.clears;
}
bool C3D_Init(std::size_t size) {
    CHECK(state.gfx && !state.c3d && size == C3D_DEFAULT_CMDBUF_SIZE);
    state.resources.emplace_back("c3d.init");
    state.c3d = state.failure != ctr_test::Failure::citro3d;
    return state.c3d;
}
void C3D_Fini() {
    CHECK(state.c3d && !state.c2d && !state.frame);
    state.c3d = state.target = false;
    state.resources.emplace_back("c3d.fini");
}
bool C2D_Init(std::size_t objects) {
    CHECK(state.c3d && !state.c2d && objects == C2D_DEFAULT_MAX_OBJECTS);
    state.resources.emplace_back("c2d.init");
    state.c2d = state.failure != ctr_test::Failure::citro2d;
    return state.c2d;
}
void C2D_Fini() {
    CHECK(state.c2d && state.c3d && !state.tone && !state.callback && !state.frame);
    // FrameEnd queues asynchronous GPU work. Vertex buffers must outlive it.
    CHECK(!state.pending_gpu);
    state.c2d = false;
    state.resources.emplace_back("c2d.fini");
}
void C2D_Prepare() {
    CHECK(state.c2d && state.c3d);
    state.resources.emplace_back("c2d.prepare");
}
C3D_RenderTarget *C2D_CreateScreenTarget(gfxScreen_t screen, gfx3dSide_t side) {
    CHECK(state.c2d && screen == GFX_TOP && side == GFX_LEFT);
    state.resources.emplace_back("target.create");
    state.target = state.failure != ctr_test::Failure::target;
    return state.target ? &screen_target : nullptr;
}
void C3D_RenderTargetDelete(C3D_RenderTarget *target) {
    CHECK(state.c3d && state.target && target == &screen_target && !state.frame);
    state.pending_gpu = false; // SDK deletion waits for queued GPU work.
    state.target = false;
    state.resources.emplace_back("target.delete");
}
bool C3D_FrameBegin(u8 flags) {
    CHECK(state.c3d && state.c2d && state.target && !state.frame && flags == C3D_FRAME_SYNCDRAW);
    ++state.begins;
    state.frame_loops.push_back(state.loops);
    state.pending_gpu = false;
    state.frame = state.frame_allowed;
    return state.frame;
}
void C3D_FrameEnd(u8 flags) {
    CHECK(state.frame && flags == 0);
    state.frame = false;
    state.pending_gpu = true;
    ++state.ends;
}
void C2D_TargetClear(C3D_RenderTarget *target, u32 color) {
    CHECK(state.frame && state.target && target == &screen_target);
    CHECK(color == C2D_Color32(20, 22, 28, 255));
}
void C2D_SceneBegin(C3D_RenderTarget *target) {
    CHECK(state.frame && state.target && target == &screen_target);
}
bool C2D_DrawRectSolid(float x, float y, float z, float width, float height, u32 color) {
    CHECK(state.frame && state.c2d && state.target);
    state.rectangles.push_back({x, y, z, width, height, color});
    return true;
}
void gfxFlushBuffers() {
    CHECK(state.gfx && !state.frame);
    ++state.flushes;
}
void gfxSwapBuffers() {
    CHECK(state.gfx && !state.frame);
    ++state.swaps;
}
void gspWaitForVBlank() {
    CHECK(state.gfx);
    ++state.waits;
}
void hidScanInput() {
    CHECK(state.gfx && state.scans == state.reads && state.scans < state.keys.size());
    CHECK(state.loops > state.scanned_loop && state.loops <= state.keys.size());
    state.scanned_loop = state.loops;
    state.input_loops.push_back(state.loops);
    ++state.scans;
}
u32 hidKeysDown() {
    CHECK(state.gfx && state.scans == state.reads + 1);
    ++state.reads;
    return state.keys.at(state.scanned_loop - 1);
}
u32 hidKeysHeld() {
    CHECK(state.gfx && state.scans == state.reads && state.scanned_loop == state.loops);
    return state.held.empty() ? state.keys.at(state.scanned_loop - 1)
                              : state.held.at(state.scanned_loop - 1);
}
bool aptMainLoop() {
    CHECK(state.gfx);
    CHECK(++state.loops <= state.keys.size() + 1);
    if (state.loops <= state.hooks.size()) {
        CHECK(state.callback);
        state.callback(state.hooks[state.loops - 1], state.context);
    }
    if (state.loops <= state.hook_batches.size()) {
        CHECK(state.callback);
        for (const auto hook : state.hook_batches[state.loops - 1]) {
            state.callback(hook, state.context);
        }
    }
    if (state.loops == state.reset_metrics_loop) {
        state.callback(APTHOOK_ONSLEEP, state.context);
        state.callback(APTHOOK_ONWAKEUP, state.context);
    }
    if (state.exit_hook) {
        CHECK(state.callback);
        state.callback(APTHOOK_ONEXIT, state.context);
    }
    return state.loops != state.apt_close_loop && state.loops <= state.keys.size();
}
void aptHook(aptHookCookie *cookie, aptHookFn callback, void *context) {
    CHECK(state.tone && !state.callback && cookie && callback && context);
    state.cookie = cookie;
    state.callback = callback;
    state.context = context;
    state.resources.emplace_back("hook.attach");
}
void aptUnhook(aptHookCookie *cookie) {
    CHECK(state.callback && cookie == state.cookie && state.tone);
    state.cookie = nullptr;
    state.callback = nullptr;
    state.context = nullptr;
    state.resources.emplace_back("hook.detach");
}

// Composition double only; test_ctr_tone separately compiles the actual tone.cpp.
namespace sh3::platform::ctr {
Tone::Tone(bool paused) noexcept {
    CHECK(state.target && !state.tone);
    state.tone = initialized_ = true;
    result_ = state.audio_result;
    status_ = state.audio_status;
    paused_ = paused;
    state.initial_tone_paused = paused;
    (void)samples_;
    (void)wave_;
    state.resources.emplace_back("tone.init");
}
Tone::~Tone() {
    CHECK(initialized_ && state.tone && !state.callback && state.target);
    state.tone = false;
    state.resources.emplace_back("tone.fini");
}
ToneSnapshot Tone::snapshot() const noexcept {
    CHECK(state.tone);
    return {status_, result_, 123, 2, 456, paused_};
}
void Tone::pause(bool paused) noexcept {
    CHECK(state.tone && state.target);
    state.pauses.push_back(paused);
    paused_ = paused;
}
} // namespace sh3::platform::ctr
