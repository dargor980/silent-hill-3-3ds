#include "room_sdk.hpp"
#include "check.hpp"
#include "sh3/platform/inspection_crc32.hpp"
#include <algorithm>
#include <cmath>
#include <cstdlib>
#include <cstring>
#include <string>

namespace {
struct Block {
    void *p{};
    std::size_t n{};
};
std::array<Block, 32> blocks{};
std::array<C3D_Tex *, 32> tex{};
struct Buffer {
    C3D_BufInfo *info{};
    const void *p{};
};
std::array<Buffer, 4> buffers{};
const void *bound{};
unsigned attribute{}, buffer_count{}, texture_attempt{}, texture_flush{};
bool bad(std::string_view name) { return room_sdk::failure == name; }
bool nth(std::string_view name, unsigned i) {
    char s[64];
    std::snprintf(s, sizeof(s), "%.*s_%u", int(name.size()), name.data(), i);
    return bad(s);
}
void *alloc(std::size_t n) {
    auto *p = std::malloc(n);
    CHECK(p);
    std::memset(p, 0, n);
    auto slot = std::find_if(blocks.begin(), blocks.end(), [](auto b) { return !b.p; });
    CHECK(slot != blocks.end());
    *slot = {p, n};
    room_sdk::bytes += n;
    room_sdk::peak = std::max(room_sdk::peak, room_sdk::bytes);
    return p;
}
void free_block(void *p) {
    auto b = std::find_if(blocks.begin(), blocks.end(), [p](auto b) { return b.p == p; });
    CHECK(b != blocks.end());
    room_sdk::bytes -= b->n;
    *b = {};
    std::free(p);
}
} // namespace
void room_sdk::reset() {
    CHECK(!active && !bytes && !callback && !open_frame && !pending && !screens && !cpu_fast);
    frames = draws = begins = waits = hooks = unhooks = live_linear = live_textures = 0;
    peak = 0;
    attribute = buffer_count = texture_attempt = texture_flush = 0;
    buffers = {};
    tex = {};
    bound = nullptr;
    length = cursor = 0;
    failure = {};
    new_model = true;
    speedups = speedup_disables = 0;
}
std::uint32_t room_sdk::dynamic_digest() {
    auto b = std::find_if(blocks.begin(), blocks.end(), [](auto v) { return v.p == buffers[1].p; });
    CHECK(b != blocks.end());
    return sh3::platform::inspection_crc32(static_cast<const std::uint8_t *>(b->p), b->n);
}
const void *room_sdk::static_data(std::size_t &size) {
    auto b = std::find_if(blocks.begin(), blocks.end(), [](auto v) { return v.p == buffers[0].p; });
    CHECK(b != blocks.end());
    size = b->n;
    return b->p;
}
bool C3D_Init(std::size_t n) {
    CHECK(n == C3D_DEFAULT_CMDBUF_SIZE);
    if (bad("CITRO3D"))
        return false;
    ++room_sdk::active;
    return true;
}
void C3D_Fini() {
    CHECK(!room_sdk::live_linear && !room_sdk::live_textures);
    --room_sdk::active;
    buffer_count = texture_attempt = texture_flush = 0;
    buffers = {};
    tex = {};
}
C3D_RenderTarget *C3D_RenderTargetCreate(int h, int w, int, int) {
    CHECK(h == 240 && w == 400);
    if (bad("TARGET"))
        return nullptr;
    return new C3D_RenderTarget;
}
void C3D_RenderTargetSetOutput(C3D_RenderTarget *, int, int, u32) {}
void C3D_RenderTargetDelete(C3D_RenderTarget *p) {
    CHECK(!room_sdk::open_frame);
    room_sdk::pending = false;
    delete p;
}
void C3D_RenderTargetClear(C3D_RenderTarget *, int, u32, u32) { CHECK(room_sdk::open_frame); }
bool C3D_FrameBegin(int f) {
    CHECK(f == C3D_FRAME_SYNCDRAW && !room_sdk::open_frame);
    ++room_sdk::begins;
    if (bad("BUSY"))
        return false;
    room_sdk::pending = false;
    room_sdk::open_frame = true;
    return true;
}
bool C3D_FrameDrawOn(C3D_RenderTarget *) {
    CHECK(room_sdk::open_frame);
    return !bad("DRAW_ON");
}
void C3D_FrameEnd(int) {
    CHECK(room_sdk::open_frame);
    room_sdk::open_frame = false;
    room_sdk::pending = true;
    ++room_sdk::frames;
}
bool C3D_TexInit(C3D_Tex *p, unsigned w, unsigned h, int) {
    unsigned i = texture_attempt++;
    if (nth("TEXTURE", i))
        return false;
    p->data = alloc(w * h * 4);
    tex[i] = p;
    ++room_sdk::live_textures;
    return true;
}
void C3D_TexDelete(C3D_Tex *p) {
    CHECK(!room_sdk::pending);
    free_block(p->data);
    --room_sdk::live_textures;
}
void C3D_TexSetFilter(C3D_Tex *, int a, int b) { CHECK(a == GPU_LINEAR && b == GPU_LINEAR); }
void C3D_TexSetWrap(C3D_Tex *p, int a, int b) {
    const auto slot = std::find(tex.begin(), tex.end(), p) - tex.begin();
    const auto mode = slot >= 14 ? GPU_REPEAT : GPU_CLAMP_TO_EDGE;
    CHECK(a == mode && b == mode);
}
void C3D_TexBind(int, C3D_Tex *p) {
    auto it = std::find(tex.begin(), tex.end(), p);
    CHECK(it != tex.end());
    room_sdk::texture = int(it - tex.begin());
}
C3D_AttrInfo *C3D_GetAttrInfo() {
    static C3D_AttrInfo a;
    return &a;
}
void AttrInfo_Init(C3D_AttrInfo *) { attribute = 0; }
int AttrInfo_AddLoader(C3D_AttrInfo *, int i, int type, int n) {
    CHECK(i == int(attribute) && type == GPU_FLOAT && n == (i == 0 ? 4 : i == 1 ? 3 : 2));
    return nth("ATTRIBUTE", attribute++) ? -1 : 0;
}
C3D_BufInfo *C3D_GetBufInfo() {
    static C3D_BufInfo b;
    return &b;
}
void BufInfo_Init(C3D_BufInfo *) {}
int BufInfo_Add(C3D_BufInfo *b, const void *p, std::ptrdiff_t stride, int n, std::uint64_t mask) {
    CHECK(stride == 36 && n == 3 && mask == 0x210);
    if (nth("BUFFER", buffer_count))
        return -1;
    CHECK(buffer_count < buffers.size());
    buffers[buffer_count++] = {b, p};
    return 0;
}
void C3D_SetBufInfo(C3D_BufInfo *b) {
    auto it = std::find_if(buffers.begin(), buffers.end(), [b](auto v) { return v.info == b; });
    CHECK(it != buffers.end());
    bound = it->p;
}
void Mtx_PerspTilt(C3D_Mtx *, float f, float aspect, float near, float far, bool) {
    CHECK(std::abs(f - C3D_AngleFromDegrees(80)) < 1e-6 && aspect == C3D_AspectRatioTop &&
          near == .02F && far == 12);
}
void Mtx_LookAt(C3D_Mtx *, C3D_FVec eye, C3D_FVec target, C3D_FVec up, bool) {
    CHECK(std::abs(eye.x - .55F) < 1e-6 && eye.y == 2 && std::abs(eye.z - 1.4F) < 1e-6);
    CHECK(std::abs(target.y - .6F) < 1e-6 && std::abs(target.z + .2F) < 1e-6 && up.y == 1);
}
void Mtx_Multiply(C3D_Mtx *, const C3D_Mtx *, const C3D_Mtx *) {}
void C3D_FVUnifMtx4x4(int, int, const C3D_Mtx *) {}
void C3D_BindProgram(shaderProgram_s *) {}
C3D_TexEnv *C3D_GetTexEnv(int) {
    static C3D_TexEnv env;
    return &env;
}
void C3D_TexEnvInit(C3D_TexEnv *) {}
void C3D_TexEnvSrc(C3D_TexEnv *, int, int, int) {}
void C3D_TexEnvFunc(C3D_TexEnv *, int, int) {}
void C3D_TexEnvColor(C3D_TexEnv *, u32 v) { CHECK(v == 0xFDFFFFFF || v == 0x00FFFFFF); }
void C3D_AlphaTest(bool on, int compare, int value) {
    room_sdk::alpha = on ? value : -1;
    CHECK(compare == GPU_ALWAYS || compare == GPU_GREATER);
}
void C3D_DepthTest(bool on, int compare, int writes) {
    CHECK(on && compare == GPU_GEQUAL);
    room_sdk::writes = writes;
}
void C3D_AlphaBlend(GPU_BLENDEQUATION, GPU_BLENDEQUATION, GPU_BLENDFACTOR src, GPU_BLENDFACTOR dst,
                    GPU_BLENDFACTOR, GPU_BLENDFACTOR) {
    room_sdk::blended = src == GPU_SRC_ALPHA;
    CHECK(dst == (room_sdk::blended ? GPU_ONE_MINUS_SRC_ALPHA : GPU_ZERO));
}
void C3D_CullFace(int c) { room_sdk::cull = c; }
void C3D_DrawArrays(int type, int first, int count) {
    using namespace room_sdk;
    CHECK(open_frame && type == GPU_TRIANGLES && first >= 0 && count > 0 && count % 3 == 0);
    auto b = std::find_if(blocks.begin(), blocks.end(), [](auto b) { return b.p == bound; });
    CHECK(b != blocks.end() && std::size_t(first + count) * 36 <= b->n);
    if (bound == buffers[0].p)
        CHECK(writes == GPU_WRITE_ALL && cull == GPU_CULL_NONE &&
              (texture >= 14 ? (alpha == -1 || alpha == 0) : (!blended && alpha == -1)));
    else if (texture == 13)
        CHECK(writes == GPU_WRITE_COLOR && blended && cull == GPU_CULL_BACK_CCW && alpha == -1);
    else if (blended)
        CHECK(writes == GPU_WRITE_COLOR && alpha == 100);
    else
        CHECK(writes == GPU_WRITE_ALL && alpha == 0);
    const auto *v = static_cast<const float *>(bound) + first * 9;
    for (int i = 0; i < count; ++i, v += 9)
        CHECK(std::isfinite(v[0]) && v[3] >= 4094.F / 4096 && v[3] <= 1);
    ++draws;
}
DVLB_s *DVLB_ParseFile(u32 *, std::size_t) {
    if (bad("SHADER"))
        return nullptr;
    auto *p = new DVLB_s;
    if (bad("EMPTY_SHADER"))
        p->numDVLE = 0;
    return p;
}
void DVLB_Free(DVLB_s *p) { delete p; }
Result shaderProgramInit(shaderProgram_s *) { return bad("PROGRAM") ? -1 : 0; }
Result shaderProgramSetVsh(shaderProgram_s *p, DVLE_s *) {
    static shaderInstance_s v;
    p->vertexShader = &v;
    return bad("VERTEX_SHADER") ? -1 : 0;
}
Result shaderProgramFree(shaderProgram_s *) { return 0; }
int shaderInstanceGetUniformLocation(shaderInstance_s *, const char *) {
    return bad("UNIFORM") ? -1 : 0;
}
void *linearAlloc(std::size_t n) {
    if (nth("LINEAR", room_sdk::live_linear))
        return nullptr;
    ++room_sdk::live_linear;
    return alloc(n);
}
void linearFree(void *p) {
    CHECK(!room_sdk::pending);
    free_block(p);
    --room_sdk::live_linear;
}
Result GSPGPU_FlushDataCache(const void *p, std::size_t) {
    if (p == buffers[1].p) {
        CHECK(room_sdk::open_frame && !room_sdk::pending);
        return bad("DYNAMIC_FLUSH") ? -1 : 0;
    }
    for (auto *t : tex)
        if (t && t->data == p)
            return nth("TEXTURE_FLUSH", texture_flush++) ? -1 : 0;
    return bad("STATIC_FLUSH") ? -1 : 0;
}
void aptHook(aptHookCookie *, void (*cb)(APT_HookType, void *), void *p) {
    CHECK(!room_sdk::callback);
    room_sdk::callback = cb;
    room_sdk::context = p;
    ++room_sdk::hooks;
}
void aptUnhook(aptHookCookie *) {
    CHECK(room_sdk::callback);
    room_sdk::callback = nullptr;
    ++room_sdk::unhooks;
}
bool aptMainLoop() {
    using namespace room_sdk;
    if (cursor == length)
        return false;
    current = script[cursor++];
    if (current.clear_failure)
        failure = {};
    if (current.event >= 0 && callback)
        callback(static_cast<APT_HookType>(current.event), context);
    return true;
}
void gfxInitDefault() {
    CHECK(!room_sdk::screens);
    room_sdk::screens = true;
}
void gfxExit() {
    CHECK(!room_sdk::active && !room_sdk::callback && !room_sdk::cpu_fast);
    room_sdk::screens = false;
}
void consoleInit(int, void *) {}
void gfxFlushBuffers() {}
void gfxSwapBuffers() {}
void gspWaitForVBlank() { ++room_sdk::waits; }
void hidScanInput() {}
u32 hidKeysHeld() { return room_sdk::current.held; }
u32 hidKeysDown() { return room_sdk::current.down; }
std::uint64_t svcGetSystemTick() { return room_sdk::current.tick; }
Result APT_CheckNew3DS(bool *is_new) {
    *is_new = room_sdk::new_model;
    return bad("CPU_QUERY") ? -1 : 0;
}
void osSetSpeedupEnable(bool enabled) {
    CHECK(room_sdk::screens);
    room_sdk::cpu_fast = enabled;
    if (enabled)
        ++room_sdk::speedups;
    else
        ++room_sdk::speedup_disables;
}
float C3D_GetDrawingTime() { return 0; }
