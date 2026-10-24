#include "renderer.hpp"
#include "material_state.hpp"
#include "scene_shader_shbin.h"
#include "sh3/platform/checker_texture.hpp"
#include <cstring>
#include <type_traits>

namespace sh3::platform::ctr {
SceneRenderer::SceneRenderer() noexcept { initialize(nullptr); }
SceneRenderer::SceneRenderer(InspectionPixels pixels) noexcept {
    if (!valid_inspection_pixels(pixels)) {
        stage_ = "TEXTURE_DATA";
        return;
    }
    initialize(&pixels);
}
SceneRenderer::SceneRenderer(InspectionMesh mesh) noexcept {
    if (!valid_inspection_mesh(mesh)) {
        stage_ = "GEOMETRY_DATA";
        return;
    }
    initialize(nullptr, &mesh);
}
SceneRenderer::SceneRenderer(InspectionMesh mesh, InspectionPixels pixels) noexcept
    : material_(true) {
    if (!valid_inspection_mesh(mesh)) {
        stage_ = "GEOMETRY_DATA";
        return;
    }
    if (!valid_inspection_pixels(pixels)) {
        stage_ = "TEXTURE_DATA";
        return;
    }
    initialize(&pixels, &mesh);
}
void SceneRenderer::initialize(const InspectionPixels *pixels,
                               const InspectionMesh *geometry) noexcept {
    mesh_mode_ = geometry && !pixels;
    static_assert(sizeof(domain::SceneVertex) == 8 * sizeof(float));
    static_assert(std::is_standard_layout_v<domain::SceneVertex>);
    citro_ready_ = C3D_Init(C3D_DEFAULT_CMDBUF_SIZE);
    if (!citro_ready_) {
        return;
    }
    stage_ = "TARGET";
    target_ = C3D_RenderTargetCreate(240, 400, GPU_RB_RGBA8, GPU_RB_DEPTH24_STENCIL8);
    if (!target_) {
        return;
    }
    constexpr u32 transfer =
        GX_TRANSFER_FLIP_VERT(0) | GX_TRANSFER_OUT_TILED(0) | GX_TRANSFER_RAW_COPY(0) |
        GX_TRANSFER_IN_FORMAT(GX_TRANSFER_FMT_RGBA8) |
        GX_TRANSFER_OUT_FORMAT(GX_TRANSFER_FMT_RGB8) | GX_TRANSFER_SCALING(GX_TRANSFER_SCALE_NO);
    C3D_RenderTargetSetOutput(target_, GFX_TOP, GFX_LEFT, transfer);
    stage_ = "SHADER";
    // libctru's parser takes non-const memory but the embedded bytecode is immutable.
    shader_ =
        DVLB_ParseFile(reinterpret_cast<u32 *>(const_cast<unsigned char *>(scene_shader_shbin)),
                       scene_shader_shbin_size);
    if (!shader_ || shader_->numDVLE < 1) {
        return;
    }
    stage_ = "PROGRAM";
    program_ready_ = R_SUCCEEDED(shaderProgramInit(&program_));
    if (!program_ready_) {
        return;
    }
    stage_ = "VERTEX_SHADER";
    if (R_FAILED(shaderProgramSetVsh(&program_, &shader_->DVLE[0]))) {
        return;
    }
    stage_ = "UNIFORM";
    transform_location_ = shaderInstanceGetUniformLocation(program_.vertexShader, "transform");
    if (transform_location_ < 0) {
        return;
    }
    stage_ = "VERTICES";
    const auto mesh = domain::synthetic_room();
    const auto panel = domain::texture_panel();
    vertex_count_ = geometry ? geometry->count : pixels ? panel.size() : mesh.size();
    const auto backdrop = domain::material_backdrop();
    const auto first = material_ ? backdrop.size() : 0;
    const auto vertex_bytes = (first + vertex_count_) * sizeof(domain::SceneVertex);
    vertices_ = linearAlloc(vertex_bytes);
    if (!vertices_) {
        return;
    }
    if (material_)
        std::memcpy(vertices_, backdrop.data(), sizeof(backdrop));
    std::memcpy(static_cast<domain::SceneVertex *>(vertices_) + first,
                geometry ? geometry->data
                : pixels ? panel.data()
                         : mesh.data(),
                vertex_count_ * sizeof(domain::SceneVertex));
    stage_ = "VERTEX_FLUSH";
    if (R_FAILED(GSPGPU_FlushDataCache(vertices_, vertex_bytes))) {
        return;
    }
    stage_ = "TEXTURE";
    const auto width = pixels ? inspection_width : checker_width;
    texture_ready_ = C3D_TexInit(&texture_, width, width, GPU_RGBA8);
    if (!texture_ready_) {
        return;
    }
    if (pixels) {
        // Both buffers and exact sizes are checked before reaching this point.
        (void)upload_inspection_pixels(*pixels, static_cast<std::uint8_t *>(texture_.data),
                                       inspection_bytes);
    } else {
        write_checker_texture(static_cast<std::uint8_t *>(texture_.data));
    }
    // The SDK's TexFlush returns void. Use the checked cache operation on this linear texture.
    stage_ = "TEXTURE_FLUSH";
    if (R_FAILED(GSPGPU_FlushDataCache(texture_.data, width * width * 4))) {
        return;
    }
    C3D_TexSetFilter(&texture_, material_ ? GPU_LINEAR : GPU_NEAREST,
                     material_ ? GPU_LINEAR : GPU_NEAREST);
    C3D_TexSetWrap(&texture_, material_ ? GPU_CLAMP_TO_EDGE : GPU_REPEAT,
                   material_ ? GPU_CLAMP_TO_EDGE : GPU_REPEAT);
    stage_ = "ATTRIBUTES";
    auto *attributes = C3D_GetAttrInfo();
    AttrInfo_Init(attributes);
    if (AttrInfo_AddLoader(attributes, 0, GPU_FLOAT, 3) < 0 ||
        AttrInfo_AddLoader(attributes, 1, GPU_FLOAT, 2) < 0 ||
        AttrInfo_AddLoader(attributes, 2, GPU_FLOAT, 3) < 0) {
        return;
    }
    stage_ = "BUFFER";
    auto *buffers = C3D_GetBufInfo();
    BufInfo_Init(buffers);
    if (BufInfo_Add(buffers, vertices_, sizeof(domain::SceneVertex), 3, 0x210) < 0) {
        return;
    }
    Mtx_PerspTilt(&projection_, C3D_AngleFromDegrees(60.0F), C3D_AspectRatioTop, 0.1F, 30.0F,
                  false);
    C3D_BindProgram(&program_);
    C3D_TexBind(0, &texture_);
    auto *environment = C3D_GetTexEnv(0);
    C3D_TexEnvInit(environment);
    C3D_TexEnvSrc(environment, C3D_Both, GPU_TEXTURE0, GPU_PRIMARY_COLOR);
    C3D_TexEnvFunc(environment, C3D_Both, GPU_MODULATE);
    C3D_AlphaBlend(GPU_BLEND_ADD, GPU_BLEND_ADD, GPU_ONE, GPU_ZERO, GPU_ONE, GPU_ZERO);
    C3D_DepthTest(true, GPU_GREATER, GPU_WRITE_ALL);
    C3D_CullFace(GPU_CULL_NONE);
    ready_ = true;
    stage_ = "READY";
}

SceneRenderer::~SceneRenderer() {
    if (target_) {
        // Citro3D waits for queued GPU work before deleting the target.
        C3D_RenderTargetDelete(target_);
    }
    if (texture_ready_) {
        C3D_TexDelete(&texture_);
    }
    if (vertices_) {
        linearFree(vertices_);
    }
    if (program_ready_) {
        shaderProgramFree(&program_);
    }
    if (shader_) {
        DVLB_Free(shader_);
    }
    if (citro_ready_) {
        C3D_Fini();
    }
}

ports::RenderResult SceneRenderer::present(const domain::OrbitCamera &camera) noexcept {
    return present_frame(camera, nullptr);
}
ports::RenderResult SceneRenderer::present_mesh(const domain::OrbitCamera &camera,
                                                const domain::SceneVertex *vertices,
                                                std::size_t count) noexcept {
    const InspectionMesh mesh{vertices, count};
    if (!mesh_mode_ || count != static_cast<std::size_t>(vertex_count_) ||
        !valid_inspection_mesh(mesh))
        return ports::RenderResult::unavailable;
    return present_frame(camera, &mesh);
}
ports::RenderResult SceneRenderer::present_frame(const domain::OrbitCamera &camera,
                                                 const InspectionMesh *mesh) noexcept {
    if (!ready_) {
        return ports::RenderResult::unavailable;
    }
    if (!domain::valid_camera(camera)) {
        return ports::RenderResult::invalid_camera;
    }
    if (!C3D_FrameBegin(C3D_FRAME_SYNCDRAW)) {
        return ports::RenderResult::busy;
    }
    // SYNCDRAW has waited for prior GPU commands before this single buffer is reused.
    if (mesh) {
        const auto bytes = mesh->count * sizeof(domain::SceneVertex);
        std::memcpy(vertices_, mesh->data, bytes);
        if (R_FAILED(GSPGPU_FlushDataCache(vertices_, bytes))) {
            C3D_FrameEnd(0);
            return ports::RenderResult::unavailable;
        }
    }
    C3D_RenderTargetClear(target_, C3D_CLEAR_ALL, 0x152333FF, 0);
    if (!C3D_FrameDrawOn(target_)) {
        C3D_FrameEnd(0);
        return ports::RenderResult::unavailable;
    }
    const auto eye = domain::camera_eye(camera);
    const auto target = camera.target;
    C3D_Mtx view, transform;
    Mtx_LookAt(&view, FVec3_New(eye.x, eye.y, eye.z), FVec3_New(target.x, target.y, target.z),
               FVec3_New(0, 1, 0), false);
    Mtx_Multiply(&transform, &projection_, &view);
    C3D_FVUnifMtx4x4(GPU_VERTEX_SHADER, transform_location_, &transform);
    if (material_) {
        bind_material_backdrop();
        C3D_DrawArrays(GPU_TRIANGLES, 0, 96);
        bind_captured_glass();
        C3D_DrawArrays(GPU_TRIANGLES, 96, vertex_count_);
    } else {
        if (mesh)
            bind_material_backdrop(); // Solid vertex colors for diagnostic bones.
        C3D_DrawArrays(GPU_TRIANGLES, 0, vertex_count_);
    }
    C3D_FrameEnd(0);
    return ports::RenderResult::presented;
}
} // namespace sh3::platform::ctr
