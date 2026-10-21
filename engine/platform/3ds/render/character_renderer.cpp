#include "character_renderer.hpp"
#include "character_shader_shbin.h"
#include "material_state.hpp"
#include <cstring>
#include <type_traits>

namespace sh3::platform::ctr {
CharacterRenderer::CharacterRenderer(std::size_t count) noexcept : count_(count) {
    static_assert(sizeof(domain::CharacterDrawVertex) == 28);
    static_assert(std::is_standard_layout_v<domain::CharacterDrawVertex>);
    if (count < 3 || count > domain::character_index_limit || count % 3)
        return;
    stage_ = "CITRO3D";
    citro_ = C3D_Init(C3D_DEFAULT_CMDBUF_SIZE);
    if (!citro_)
        return;
    stage_ = "TARGET";
    target_ = C3D_RenderTargetCreate(240, 400, GPU_RB_RGBA8, GPU_RB_DEPTH24_STENCIL8);
    if (!target_)
        return;
    constexpr u32 transfer =
        GX_TRANSFER_FLIP_VERT(0) | GX_TRANSFER_OUT_TILED(0) | GX_TRANSFER_RAW_COPY(0) |
        GX_TRANSFER_IN_FORMAT(GX_TRANSFER_FMT_RGBA8) |
        GX_TRANSFER_OUT_FORMAT(GX_TRANSFER_FMT_RGB8) | GX_TRANSFER_SCALING(GX_TRANSFER_SCALE_NO);
    C3D_RenderTargetSetOutput(target_, GFX_TOP, GFX_LEFT, transfer);
    stage_ = "SHADER";
    shader_ =
        DVLB_ParseFile(reinterpret_cast<u32 *>(const_cast<unsigned char *>(character_shader_shbin)),
                       character_shader_shbin_size);
    if (!shader_ || shader_->numDVLE < 1)
        return;
    stage_ = "PROGRAM";
    program_ready_ = R_SUCCEEDED(shaderProgramInit(&program_));
    if (!program_ready_)
        return;
    stage_ = "VERTEX_SHADER";
    if (R_FAILED(shaderProgramSetVsh(&program_, &shader_->DVLE[0])))
        return;
    stage_ = "UNIFORM";
    uniform_ = shaderInstanceGetUniformLocation(program_.vertexShader, "transform");
    if (uniform_ < 0)
        return;
    stage_ = "VERTICES";
    vertices_ = linearAlloc(count * sizeof(domain::CharacterDrawVertex));
    if (!vertices_)
        return;
    stage_ = "ATTRIBUTES";
    auto *attributes = C3D_GetAttrInfo();
    AttrInfo_Init(attributes);
    if (AttrInfo_AddLoader(attributes, 0, GPU_FLOAT, 4) < 0 ||
        AttrInfo_AddLoader(attributes, 1, GPU_FLOAT, 3) < 0)
        return;
    stage_ = "BUFFER";
    auto *buffers = C3D_GetBufInfo();
    BufInfo_Init(buffers);
    if (BufInfo_Add(buffers, vertices_, sizeof(domain::CharacterDrawVertex), 2, 0x10) < 0)
        return;
    Mtx_PerspTilt(&projection_, C3D_AngleFromDegrees(60.0F), C3D_AspectRatioTop, 0.1F, 30.0F,
                  false);
    C3D_BindProgram(&program_);
    bind_material_backdrop();
    stage_ = "READY";
    ready_ = true;
}
CharacterRenderer::~CharacterRenderer() {
    // Target deletion waits for pending commands before any referenced memory is freed.
    if (target_)
        C3D_RenderTargetDelete(target_);
    if (vertices_)
        linearFree(vertices_);
    if (program_ready_)
        shaderProgramFree(&program_);
    if (shader_)
        DVLB_Free(shader_);
    if (citro_)
        C3D_Fini();
}
ports::RenderResult CharacterRenderer::present(const domain::OrbitCamera &camera,
                                               const domain::CharacterDrawVertex *mesh,
                                               std::size_t count) noexcept {
    using R = ports::RenderResult;
    if (!ready_ || count != count_ || !domain::valid_character_draw(mesh, count))
        return R::unavailable;
    if (!domain::valid_camera(camera))
        return R::invalid_camera;
    if (!C3D_FrameBegin(C3D_FRAME_SYNCDRAW))
        return R::busy;
    // The preceding frame no longer owns this buffer. First upload also happens here.
    const auto bytes = count * sizeof(domain::CharacterDrawVertex);
    std::memcpy(vertices_, mesh, bytes);
    if (R_FAILED(GSPGPU_FlushDataCache(vertices_, bytes))) {
        C3D_FrameEnd(0);
        return R::unavailable;
    }
    C3D_RenderTargetClear(target_, C3D_CLEAR_ALL, 0x152333FF, 0);
    if (!C3D_FrameDrawOn(target_)) {
        C3D_FrameEnd(0);
        return R::unavailable;
    }
    const auto eye = domain::camera_eye(camera), target = domain::camera_target;
    C3D_Mtx view, transform;
    Mtx_LookAt(&view, FVec3_New(eye.x, eye.y, eye.z), FVec3_New(target.x, target.y, target.z),
               FVec3_New(0, 1, 0), false);
    Mtx_Multiply(&transform, &projection_, &view);
    C3D_FVUnifMtx4x4(GPU_VERTEX_SHADER, uniform_, &transform);
    bind_material_backdrop();
    C3D_DrawArrays(GPU_TRIANGLES, 0, static_cast<int>(count));
    C3D_FrameEnd(0);
    return R::presented;
}
} // namespace sh3::platform::ctr
