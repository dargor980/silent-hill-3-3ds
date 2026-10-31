#include "skinning_gpu.hpp"
#include "room_material_state.hpp"
#include "skinning_shader_shbin.h"
#include <new>

namespace sh3::platform::ctr {
SkinningGpu::SkinningGpu(const domain::InspectionRig &model, std::size_t budget) noexcept {
    bytes_ = sizeof(*this) + sizeof(domain::SkinPlanWorkspace);
    if (bytes_ > budget) {
        stage_ = "HS_BUDGET";
        return;
    }
    auto work =
        std::unique_ptr<domain::SkinPlanWorkspace>(new (std::nothrow) domain::SkinPlanWorkspace{});
    if (!work)
        return;
    stage_ = "HS_PLAN";
    if (!domain::skin_plan(model, *work, counts_))
        return;
    // Include simultaneous preparation scratch, not just the live draw buffers.
    const auto planned = bytes_ + counts_.bytes();
    stage_ = "HS_BUDGET";
    if (planned > budget || !counts_.batches)
        return;
    bytes_ = planned;
    stage_ = "HS_BUFFERS";
    batches_.reset(new (std::nothrow) domain::SkinBatch[counts_.batches]);
    vertices_ = linearAlloc(counts_.vertices * sizeof(domain::SkinVertex));
    indices_ = linearAlloc(counts_.indices * sizeof(std::uint16_t));
    if (!batches_ || !vertices_ || !indices_)
        return;
    domain::SkinStorage storage{static_cast<domain::SkinVertex *>(vertices_),
                                static_cast<std::uint16_t *>(indices_), batches_.get(), counts_};
    if (!domain::skin_plan(model, *work, counts_, &storage))
        return;
    stage_ = "HS_FLUSH";
    if (R_FAILED(GSPGPU_FlushDataCache(vertices_, counts_.vertices * sizeof(domain::SkinVertex))) ||
        R_FAILED(GSPGPU_FlushDataCache(indices_, counts_.indices * sizeof(std::uint16_t))))
        return;
    stage_ = "HS_SHADER";
    shader_ =
        DVLB_ParseFile(reinterpret_cast<u32 *>(const_cast<unsigned char *>(skinning_shader_shbin)),
                       skinning_shader_shbin_size);
    if (!shader_ || !shader_->numDVLE)
        return;
    stage_ = "HS_PROGRAM";
    program_ready_ = R_SUCCEEDED(shaderProgramInit(&program_));
    if (!program_ready_ || R_FAILED(shaderProgramSetVsh(&program_, &shader_->DVLE[0])))
        return;
    stage_ = "HS_UNIFORMS";
    if (shaderInstanceGetUniformLocation(program_.vertexShader, "palette") != 0 ||
        shaderInstanceGetUniformLocation(program_.vertexShader, "clip_from_room") != 90)
        return;
    stage_ = "HS_ATTRIBUTES";
    AttrInfo_Init(&attributes_);
    for (int i = 0; i < 4; ++i)
        if (AttrInfo_AddLoader(&attributes_, i, GPU_FLOAT, 4) < 0)
            return;
    stage_ = "HS_BUFFER_INFO";
    BufInfo_Init(&buffer_);
    if (BufInfo_Add(&buffer_, vertices_, sizeof(domain::SkinVertex), 4, 0x3210) < 0)
        return;
    stage_ = "HS_READY";
    ready_ = true;
}
SkinningGpu::~SkinningGpu() {
    if (vertices_)
        linearFree(vertices_);
    if (indices_)
        linearFree(indices_);
    if (program_ready_)
        shaderProgramFree(&program_);
    if (shader_)
        DVLB_Free(shader_);
}
bool SkinningGpu::prepare(const domain::RigPalette &palette,
                          const domain::PoseMatrix &instance) noexcept {
    return ready_ && domain::skin_rows(palette, instance, scratch_, rows_);
}
void SkinningGpu::draw(const C3D_Mtx &camera, C3D_Tex *textures) noexcept {
    C3D_BindProgram(&program_);
    C3D_SetAttrInfo(&attributes_);
    C3D_SetBufInfo(&buffer_);
    C3D_FVUnifMtx4x4(GPU_VERTEX_SHADER, 90, &camera);
    for (std::size_t i = 0; i < counts_.batches; ++i) {
        const auto &b = batches_[i];
        // Plan is immutable and validated: 1..30 matrices => 3..90 rows.
        auto *uniforms = C3D_FVUnifWritePtr(GPU_VERTEX_SHADER, 0, 3 * b.matrix_count);
        for (unsigned j = 0; j < b.matrix_count; ++j)
            for (unsigned r = 0; r < 3; ++r) {
                const auto &row = rows_[b.slots[j]][r];
                uniforms[3 * j + r] = FVec4_New(row[0], row[1], row[2], row[3]);
            }
        (void)bind_room_material(domain::RoomPass::opaque);
        C3D_TexBind(0, &textures[b.material]);
        C3D_DrawElements(GPU_TRIANGLES, int(b.count), C3D_UNSIGNED_SHORT,
                         static_cast<const std::uint16_t *>(indices_) + b.first);
    }
}
} // namespace sh3::platform::ctr
