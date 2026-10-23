#include "character_renderer.hpp"
#include "character_shader_shbin.h"
#include "material_state.hpp"
#include <cstring>
#include <type_traits>

namespace sh3::platform::ctr {
CharacterRenderer::CharacterRenderer(std::size_t count, const CharacterMaterialData *material,
                                     std::size_t instances) noexcept
    : count_(count), instances_(instances) {
    static_assert(sizeof(domain::CharacterDrawVertex) == 36);
    static_assert(std::is_standard_layout_v<domain::CharacterDrawVertex>);
    if (count < 3 || count > domain::character_index_limit || count % 3 || instances < 1 ||
        instances > 3)
        return;
    if (material && !domain::valid_character_materials(material->ranges, count)) {
        stage_ = "MATERIAL";
        return;
    }
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
    vertices_ = linearAlloc(count * instances * sizeof(domain::CharacterDrawVertex));
    if (!vertices_)
        return;
    stage_ = "ATTRIBUTES";
    auto *attributes = C3D_GetAttrInfo();
    AttrInfo_Init(attributes);
    if (AttrInfo_AddLoader(attributes, 0, GPU_FLOAT, 4) < 0 ||
        AttrInfo_AddLoader(attributes, 1, GPU_FLOAT, 3) < 0 ||
        AttrInfo_AddLoader(attributes, 2, GPU_FLOAT, 2) < 0)
        return;
    stage_ = "BUFFER";
    auto *buffers = C3D_GetBufInfo();
    BufInfo_Init(buffers);
    if (BufInfo_Add(buffers, vertices_, sizeof(domain::CharacterDrawVertex), 3, 0x210) < 0)
        return;
    if (material) {
        ranges_ = material->ranges;
        for (auto &texture : textures_) {
            stage_ = "TEXTURE";
            if (!C3D_TexInit(&texture, character_texture_width, character_texture_width, GPU_RGBA8))
                return;
            const auto index = texture_count_++;
            stage_ = "PIXELS";
            if (!upload_character_texture(material->pixels.data() + index * character_texture_bytes,
                                          character_texture_bytes,
                                          static_cast<std::uint8_t *>(texture.data),
                                          character_texture_bytes))
                return;
            stage_ = "TEXTURE_FLUSH";
            if (R_FAILED(GSPGPU_FlushDataCache(texture.data, character_texture_bytes)))
                return;
            C3D_TexSetFilter(&texture, GPU_LINEAR, GPU_LINEAR);
            C3D_TexSetWrap(&texture, GPU_CLAMP_TO_EDGE, GPU_CLAMP_TO_EDGE);
        }
    }
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
    for (std::size_t i = 0; i < texture_count_; ++i)
        C3D_TexDelete(&textures_[i]);
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
    if (!ready_ || !mesh || count != count_ * instances_)
        return R::unavailable;
    for (std::size_t i = 0; i < instances_; ++i)
        if (!domain::valid_character_draw(mesh + i * count_, count_))
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
    if (texture_count_) {
        bind_character_material();
        for (std::size_t i = 0; i < instances_; ++i)
            for (const auto &range : ranges_) {
                C3D_TexBind(0, &textures_[range.texture]);
                C3D_DrawArrays(GPU_TRIANGLES, static_cast<int>(i * count_ + range.first),
                               static_cast<int>(range.count));
            }
    } else {
        bind_material_backdrop();
        C3D_DrawArrays(GPU_TRIANGLES, 0, static_cast<int>(count));
    }
    C3D_FrameEnd(0);
    return R::presented;
}
} // namespace sh3::platform::ctr
