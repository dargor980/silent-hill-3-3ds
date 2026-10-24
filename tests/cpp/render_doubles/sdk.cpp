#include "sdk.hpp"
#include "check.hpp"
#include "citro3d.h"
#include "sh3/domain/render_scene.hpp"
#include <cmath>
#include <cstdlib>
#include <cstring>

namespace {
using namespace render_sdk;
bool fails(const char *name) {
    events.emplace_back(name);
    return failure == name;
}
void acquire() {
    ++acquired;
    ++allocations;
}
void release(const char *name) {
    CHECK(!pending && !open_frame);
    events.emplace_back(name);
    ++released;
}
void *vertex_buffer = nullptr;
C3D_RenderTarget target;
DVLB_s shader;
shaderInstance_s vertex_shader;
C3D_AttrInfo attributes;
C3D_BufInfo buffers;
C3D_TexEnv environment;
std::vector<C3D_Tex *> texture_order;
C3D_Tex *bound_texture = nullptr;
int depth_mask = 0, culling = GPU_CULL_NONE, source_rgb = 0, source_alpha = 0;
int alpha_factor = 0, rgb_operation = 0;
int rig_alpha_reference = -1;
u32 constant_color = 0;
} // namespace
bool C3D_Init(std::size_t size) {
    CHECK(size == C3D_DEFAULT_CMDBUF_SIZE);
    if (fails("CITRO3D"))
        return false;
    acquire();
    return true;
}
void C3D_Fini() { release("fini"); }
C3D_RenderTarget *C3D_RenderTargetCreate(int w, int h, int color, int depth) {
    CHECK(w == 240 && h == 400 && color == GPU_RB_RGBA8 && depth == GPU_RB_DEPTH24_STENCIL8);
    if (fails("TARGET"))
        return nullptr;
    acquire();
    return &target;
}
void C3D_RenderTargetSetOutput(C3D_RenderTarget *p, int, int, u32) { CHECK(p == &target); }
void C3D_RenderTargetDelete(C3D_RenderTarget *p) {
    CHECK(p == &target && !open_frame);
    pending = false;
    release("target_delete");
}
DVLB_s *DVLB_ParseFile(u32 *, std::size_t size) {
    CHECK(size != 0);
    if (fails("SHADER"))
        return nullptr;
    shader.numDVLE = failure == "EMPTY_SHADER" ? 0 : 1;
    acquire();
    return &shader;
}
void DVLB_Free(DVLB_s *p) {
    CHECK(p == &shader);
    release("shader_free");
}
Result shaderProgramInit(shaderProgram_s *) {
    if (fails("PROGRAM"))
        return -1;
    acquire();
    return 0;
}
Result shaderProgramSetVsh(shaderProgram_s *p, DVLE_s *v) {
    CHECK(v == &shader.DVLE[0]);
    if (fails("VERTEX_SHADER"))
        return -1;
    p->vertexShader = &vertex_shader;
    return 0;
}
Result shaderProgramFree(shaderProgram_s *) {
    release("program_free");
    return 0;
}
int shaderInstanceGetUniformLocation(shaderInstance_s *p, const char *name) {
    CHECK(p == &vertex_shader && std::strcmp(name, "transform") == 0);
    return fails("UNIFORM") ? -1 : 3;
}
void *linearAlloc(std::size_t size) {
    CHECK(size == (rig ? expected_vertices.size() : character ? (character_material ? 324U : 108U)*character_instances : (material ? 99U : geometry ? 3U : inspection ? 6U : 60U) * 32));
    if (fails("VERTICES"))
        return nullptr;
    acquire();
    vertex_buffer = std::malloc(size);
    return vertex_buffer;
}
void linearFree(void *p) {
    CHECK(p);
    release("vertices_free");
    std::free(p);
}
Result GSPGPU_FlushDataCache(const void *p, std::size_t size) {
    CHECK(p);
    const bool vertex_flush = p == vertex_buffer;
    if (dynamic && vertex_flush && frames) CHECK(open_frame && !pending);
    CHECK(size == (rig ? (vertex_flush ? expected_vertices.size() : rig_dimensions[texture_flushes].first*rig_dimensions[texture_flushes].second*4) : vertex_flush ? (character ? (character_material ? 324U : 108U)*character_instances : material     ? 3168U
                                   : geometry     ? 96U
                                   : inspection ? 192U
                                                : 1920U)
                                : (character_material ? 1048576U : inspection ? 262144U : 16384U)));
    if ((geometry || character) && vertex_flush) {
        const auto *bytes = static_cast<const unsigned char *>(p);
        if (material) {
            const auto backdrop = sh3::domain::material_backdrop();
            CHECK(std::memcmp(bytes, backdrop.data(), sizeof(backdrop)) == 0);
            bytes += sizeof(backdrop);
        }
        CHECK(std::memcmp(bytes, expected_vertices.data(), expected_vertices.size()) == 0);
    }
    if (!vertex_flush && (character_material || rig) && failure == "TEXTURE_FLUSH_" + std::to_string(texture_flushes++)) return -1;
    return fails(vertex_flush ? "VERTEX_FLUSH" : "TEXTURE_FLUSH") ? -1 : 0;
}
bool C3D_TexInit(C3D_Tex *p, unsigned w, unsigned h, int format) {
    if (rig) CHECK(w == rig_dimensions[texture_attempts].first && h == rig_dimensions[texture_attempts].second && format == GPU_RGBA8);
    else CHECK(w == (character_material ? 512U : inspection ? 256U : 64U) && h == w && format == GPU_RGBA8);
    if (failure == "TEXTURE_" + std::to_string(texture_attempts++) || fails("TEXTURE"))
        return false;
    acquire();
    texture_order.push_back(p);
    p->data = std::malloc(w * h * 4);
    return true;
}
void C3D_TexDelete(C3D_Tex *p) {
    CHECK(p->data);
    release("texture_free");
    std::free(p->data);
}
void C3D_TexSetFilter(C3D_Tex *, int min, int mag) {
    CHECK(min == ((material || character_material || rig) ? GPU_LINEAR : GPU_NEAREST) && mag == min);
}
void C3D_TexSetWrap(C3D_Tex *, int s, int t) {
    CHECK(s == ((material || character_material || rig) ? GPU_CLAMP_TO_EDGE : GPU_REPEAT) && t == s);
}
void C3D_TexBind(int unit, C3D_Tex *p) { CHECK(unit == 0 && p->data); bound_texture = p; }
C3D_AttrInfo *C3D_GetAttrInfo() { return &attributes; }
void AttrInfo_Init(C3D_AttrInfo *) {}
int AttrInfo_AddLoader(C3D_AttrInfo *, int reg, int type, int count) {
    CHECK(type == GPU_FLOAT && reg >= 0 && reg <= 2);
    CHECK(count == (character ? (reg == 0 ? 4 : reg == 1 ? 3 : 2) : (reg == 1 ? 2 : 3)));
    if (fails("ATTRIBUTES") || failure == "ATTRIBUTES_" + std::to_string(reg))
        return -1;
    return reg;
}
C3D_BufInfo *C3D_GetBufInfo() { return &buffers; }
void BufInfo_Init(C3D_BufInfo *) {}
int BufInfo_Add(C3D_BufInfo *, const void *p, std::ptrdiff_t stride, int count,
                std::uint64_t perm) {
    CHECK(p && stride == (character ? 36 : 32) && count == 3 && perm == 0x210U);
    return fails("BUFFER") ? -1 : 0;
}
void Mtx_PerspTilt(C3D_Mtx *, float fov, float aspect, float near, float far, bool left) {
    CHECK(std::abs(fov - 1.04719755F) < 0.00001F && aspect == C3D_AspectRatioTop);
    CHECK(near == 0.1F && far == 30 && !left);
}
void Mtx_LookAt(C3D_Mtx *, C3D_FVec eye, C3D_FVec target_position, C3D_FVec up, bool left) {
    CHECK(std::isfinite(eye.x) && std::isfinite(eye.y) && std::isfinite(eye.z));
    CHECK(target_position.x == expected_focus[0] && target_position.y == expected_focus[1] &&
          target_position.z == expected_focus[2]);
    CHECK(up.x == 0 && up.y == 1 && up.z == 0 && !left);
}
void Mtx_Multiply(C3D_Mtx *, const C3D_Mtx *, const C3D_Mtx *) {}
void C3D_FVUnifMtx4x4(int type, int location, const C3D_Mtx *) {
    CHECK(type == GPU_VERTEX_SHADER && location == 3 && open_frame);
}
void C3D_BindProgram(shaderProgram_s *p) { CHECK(p->vertexShader); }
C3D_TexEnv *C3D_GetTexEnv(int unit) {
    CHECK(unit == 0);
    return &environment;
}
void C3D_TexEnvInit(C3D_TexEnv *) { constant_color = 0xFFFFFFFF; }
void C3D_TexEnvSrc(C3D_TexEnv *, int mode, int texture, int color) {
    if (mode & C3D_RGB) source_rgb = texture;
    if (mode & C3D_Alpha) source_alpha = color;
    if (!material && !dynamic)
        CHECK(mode == C3D_Both && texture == GPU_TEXTURE0 && color == GPU_PRIMARY_COLOR);
}
void C3D_TexEnvFunc(C3D_TexEnv *, int mode, int operation) {
    CHECK(mode == C3D_Both && (operation == GPU_MODULATE || ((material || dynamic) && operation == GPU_REPLACE)));
    rgb_operation = operation;
}
void C3D_TexEnvColor(C3D_TexEnv *, u32 color) { constant_color = color; }
void C3D_AlphaTest(bool enabled, int op, int reference) {
    if (rig && enabled) { CHECK(op == GPU_GREATER && (reference == 0 || reference == 100)); rig_alpha_reference=reference; }
    else CHECK(!enabled && op == GPU_ALWAYS && reference == 0);
}
void C3D_DepthTest(bool enable, int operation, int mask) {
    CHECK(enable && (operation == GPU_GREATER || ((material || dynamic) && operation == GPU_GEQUAL)));
    CHECK(mask == GPU_WRITE_ALL || (material && mask == GPU_WRITE_COLOR));
    depth_mask = mask;
}
void C3D_AlphaBlend(GPU_BLENDEQUATION color, GPU_BLENDEQUATION alpha, GPU_BLENDFACTOR src,
                    GPU_BLENDFACTOR dst, GPU_BLENDFACTOR src_a, GPU_BLENDFACTOR dst_a) {
    CHECK(color == GPU_BLEND_ADD && alpha == GPU_BLEND_ADD);
    CHECK(src_a == GPU_ONE && dst_a == GPU_ZERO);
    CHECK((src == GPU_ONE && dst == GPU_ZERO) ||
          ((material || rig) && src == GPU_SRC_ALPHA && dst == GPU_ONE_MINUS_SRC_ALPHA));
    alpha_factor = src;
}
void C3D_CullFace(int mode) {
    CHECK(mode == GPU_CULL_NONE || (material && mode == GPU_CULL_BACK_CCW));
    culling = mode;
}
bool C3D_FrameBegin(int flags) {
    CHECK(flags == C3D_FRAME_SYNCDRAW && !open_frame);
    if (fails("FRAME_BEGIN"))
        return false;
    open_frame = true;
    pending = false;
    return true;
}
void C3D_RenderTargetClear(C3D_RenderTarget *p, int mask, u32, u32 depth) {
    CHECK(p == &target && open_frame && mask == C3D_CLEAR_ALL && depth == 0);
}
bool C3D_FrameDrawOn(C3D_RenderTarget *p) {
    CHECK(p == &target && open_frame);
    return !fails("DRAW_ON");
}
void C3D_DrawArrays(int mode, int first, int count) {
    CHECK(open_frame && mode == GPU_TRIANGLES);
    if (rig) {
        const auto index=draws%rig_dimensions.size();const bool blend=index+1==rig_dimensions.size();
        CHECK(texture_order.size()==rig_dimensions.size() && bound_texture==texture_order[index]);
        CHECK(first==static_cast<int>(index)*3 && count==3);
        CHECK(depth_mask==GPU_WRITE_ALL && alpha_factor==(blend?GPU_SRC_ALPHA:GPU_ONE) && culling==GPU_CULL_NONE);
        CHECK(rig_alpha_reference==(blend?100:0));
        CHECK(source_rgb==GPU_TEXTURE0 && source_alpha==GPU_PRIMARY_COLOR && rgb_operation==GPU_MODULATE);
    } else if (character_material) {
        CHECK(texture_order.size() == 3 && bound_texture == texture_order[draws % 3]);
        CHECK(first == (draws % (3*static_cast<int>(character_instances))) * 3 && count == 3);
        CHECK(depth_mask == GPU_WRITE_ALL && alpha_factor == GPU_ONE && culling == GPU_CULL_NONE);
        CHECK(source_rgb == GPU_TEXTURE0 && source_alpha == GPU_PRIMARY_COLOR && rgb_operation == GPU_MODULATE);
    } else if (material) {
        const bool glass = draws % 2 == 1;
        CHECK(first == (glass ? 96 : 0) && count == (glass ? 3 : 96));
        CHECK(depth_mask == (glass ? GPU_WRITE_COLOR : GPU_WRITE_ALL));
        CHECK(alpha_factor == (glass ? GPU_SRC_ALPHA : GPU_ONE));
        CHECK(culling == (glass ? GPU_CULL_BACK_CCW : GPU_CULL_NONE));
        CHECK(source_rgb == (glass ? GPU_TEXTURE0 : GPU_PRIMARY_COLOR));
        CHECK(source_alpha == (glass ? GPU_CONSTANT : GPU_PRIMARY_COLOR));
        CHECK(rgb_operation == (glass ? GPU_MODULATE : GPU_REPLACE));
        CHECK(constant_color == (glass ? 0xFDFFFFFF : 0xFFFFFFFF));
    } else {
        if (dynamic) CHECK(source_rgb == GPU_PRIMARY_COLOR && rgb_operation == GPU_REPLACE);
        CHECK(first == 0 &&
          count == (character || geometry ? 3
                    : inspection ? 6
                                 : 60));
    }
    ++draws;
}
void C3D_FrameEnd(int flags) {
    CHECK(flags == 0 && open_frame);
    open_frame = false;
    pending = true;
    ++frames;
}
