#include "room_renderer.hpp"
#include "character_shader_shbin.h"
#include "room_material_state.hpp"
#include "sh3/platform/inspection_crc32.hpp"
#include "sh3/platform/inspection_rig.hpp"
#include "sh3/platform/inspection_texture.hpp"
#include <cstring>
#include <new>

namespace sh3::platform::ctr {
RoomRenderer::RoomRenderer(const domain::RoomMap &map, const domain::InspectionRig &model,
                           ports::IRigTextures &source) noexcept
    : scene_(map, model) {
    const auto &memory = scene_.memory();
    if (!scene_.ready() || model.material_count != 13 ||
        memory.total + room_runtime_extra > 64 * 1024 * 1024)
        return;
    bytes_ = memory.total + room_runtime_extra;
    stage_ = "CPU_BUFFERS";
    frame_.reset(new (std::nothrow) domain::RoomFrame{});
    workspace_.reset(new (std::nothrow) domain::RoomWorkspace{});
    if (!frame_ || !workspace_)
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
    if (!shader_ || !shader_->numDVLE)
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
    stage_ = "STATIC_BUFFER";
    const auto map_bytes = map.vertex_count * sizeof(domain::CharacterDrawVertex);
    static_vertices_ = linearAlloc(map_bytes);
    if (!static_vertices_)
        return;
    std::memcpy(static_vertices_, map.vertices.data(), map_bytes);
    domain::room_diagnostic_colors(map,
                                   static_cast<domain::CharacterDrawVertex *>(static_vertices_));
    if (R_FAILED(GSPGPU_FlushDataCache(static_vertices_, map_bytes)))
        return;
    stage_ = "DYNAMIC_BUFFER";
    dynamic_vertices_ =
        linearAlloc(domain::room_dynamic_vertices * sizeof(domain::CharacterDrawVertex));
    if (!dynamic_vertices_)
        return;
    stage_ = "ATTRIBUTES";
    auto *attr = C3D_GetAttrInfo();
    AttrInfo_Init(attr);
    if (AttrInfo_AddLoader(attr, 0, GPU_FLOAT, 4) < 0 ||
        AttrInfo_AddLoader(attr, 1, GPU_FLOAT, 3) < 0 ||
        AttrInfo_AddLoader(attr, 2, GPU_FLOAT, 2) < 0)
        return;
    stage_ = "BUFFER_INFO";
    BufInfo_Init(&static_buffer_);
    BufInfo_Init(&dynamic_buffer_);
    if (BufInfo_Add(&static_buffer_, static_vertices_, sizeof(domain::CharacterDrawVertex), 3,
                    0x210) < 0 ||
        BufInfo_Add(&dynamic_buffer_, dynamic_vertices_, sizeof(domain::CharacterDrawVertex), 3,
                    0x210) < 0)
        return;
    stage_ = "TEXTURE_STAGING";
    std::unique_ptr<std::uint8_t[]> pixels(new (std::nothrow) std::uint8_t[memory.texture_staging]);
    if (!pixels)
        return;
    for (unsigned i = 0; i <= model.material_count + map.material_count; ++i) {
        const bool glass = i == model.material_count;
        const bool room = i > model.material_count;
        domain::RigMaterial m{};
        if (room) {
            const auto &t = map.materials[i - model.material_count - 1];
            m = {0, 0, i, t.width, t.height, 0, t.crc};
        } else
            m = glass ? domain::RigMaterial{0, 96, 13, 256, 256, 1, map.glass_crc}
                      : model.materials[i];
        const auto bytes = std::size_t(m.width) * m.height * 4;
        stage_ = "TEXTURE_READ";
        if (!source.read(m, pixels.get(), bytes) || inspection_crc32(pixels.get(), bytes) != m.crc)
            return;
        stage_ = "TEXTURE";
        auto &texture = textures_[i];
        if (!C3D_TexInit(&texture, m.width, m.height, GPU_RGBA8))
            return;
        ++texture_count_;
        auto *dst = static_cast<std::uint8_t *>(texture.data);
        // Sizes and non-aliasing are established above; each uploader keeps its own
        // orientation/alpha.
        if (room)
            (void)upload_room_texture(pixels.get(), bytes, dst, bytes);
        else if (glass)
            (void)upload_inspection_pixels({pixels.get(), bytes}, dst, bytes);
        else
            (void)upload_rig_texture(m, pixels.get(), bytes, dst, bytes);
        stage_ = "TEXTURE_FLUSH";
        if (R_FAILED(GSPGPU_FlushDataCache(texture.data, bytes)))
            return;
        C3D_TexSetFilter(&texture, GPU_LINEAR, GPU_LINEAR);
        C3D_TexSetWrap(&texture, room ? GPU_REPEAT : GPU_CLAMP_TO_EDGE,
                       room ? GPU_REPEAT : GPU_CLAMP_TO_EDGE);
    }
    const auto camera = domain::room_camera();
    Mtx_PerspTilt(&projection_, C3D_AngleFromDegrees(camera.fov), C3D_AspectRatioTop,
                  camera.near_plane, camera.far_plane, false);
    stage_ = "READY";
    ready_ = true;
}
RoomRenderer::~RoomRenderer() {
    // Synchronize target ownership before freeing any memory a pending draw may reference.
    if (target_)
        C3D_RenderTargetDelete(target_);
    for (std::size_t i = 0; i < texture_count_; ++i)
        C3D_TexDelete(&textures_[i]);
    if (static_vertices_)
        linearFree(static_vertices_);
    if (dynamic_vertices_)
        linearFree(dynamic_vertices_);
    if (program_ready_)
        shaderProgramFree(&program_);
    if (shader_)
        DVLB_Free(shader_);
    if (citro_)
        C3D_Fini();
}
ports::RenderResult RoomRenderer::present(const domain::RigPose &pose,
                                          const domain::PoseMatrix &instance) noexcept {
    using R = ports::RenderResult;
    const auto start = svcGetSystemTick();
    if (!ready_ || !scene_.frame(pose, instance, *workspace_, *frame_))
        return R::unavailable;
    const auto submitted = svcGetSystemTick();
    prepare_ms_ = double(submitted - start) * 1000 / SYSCLOCK_ARM11;
    if (!C3D_FrameBegin(C3D_FRAME_SYNCDRAW))
        return R::busy;
    const auto bytes = frame_->vertex_count * sizeof(domain::CharacterDrawVertex);
    std::memcpy(dynamic_vertices_, frame_->vertices.data(), bytes);
    if (R_FAILED(GSPGPU_FlushDataCache(dynamic_vertices_, bytes))) {
        C3D_FrameEnd(0);
        return R::unavailable;
    }
    C3D_RenderTargetClear(target_, C3D_CLEAR_ALL, 0x152333FF, 0);
    if (!C3D_FrameDrawOn(target_)) {
        C3D_FrameEnd(0);
        return R::unavailable;
    }
    const auto c = domain::room_camera();
    C3D_Mtx view, transform;
    Mtx_LookAt(&view, FVec3_New(c.eye.x, c.eye.y, c.eye.z),
               FVec3_New(c.target.x, c.target.y, c.target.z), FVec3_New(0, 1, 0), false);
    Mtx_Multiply(&transform, &projection_, &view);
    C3D_BindProgram(&program_);
    C3D_FVUnifMtx4x4(GPU_VERTEX_SHADER, uniform_, &transform);
    for (unsigned i = 0; i < frame_->range_count; ++i) {
        const auto &r = frame_->ranges[i];
        (void)bind_room_material(r.pass); // Plan was validated/built in the pure core.
        const bool neutral = r.pass == domain::RoomPass::neutral;
        C3D_SetBufInfo(neutral || domain::room_map_pass(r.pass) ? &static_buffer_
                                                                : &dynamic_buffer_);
        if (!neutral)
            C3D_TexBind(0, &textures_[r.texture]);
        C3D_DrawArrays(GPU_TRIANGLES, int(r.first), int(r.count));
    }
    C3D_FrameEnd(0);
    submit_ms_ = double(svcGetSystemTick() - submitted) * 1000 / SYSCLOCK_ARM11;
    return R::presented;
}
} // namespace sh3::platform::ctr
