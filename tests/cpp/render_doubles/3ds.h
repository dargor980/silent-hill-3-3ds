#pragma once
#include <cstddef>
#include <cstdint>

using u32 = std::uint32_t;
using Result = std::int32_t;
#define R_FAILED(value) ((value) < 0)
#define R_SUCCEEDED(value) ((value) >= 0)
#define GX_TRANSFER_FLIP_VERT(value) (value)
#define GX_TRANSFER_OUT_TILED(value) (value)
#define GX_TRANSFER_RAW_COPY(value) (value)
#define GX_TRANSFER_IN_FORMAT(value) (value)
#define GX_TRANSFER_OUT_FORMAT(value) (value)
#define GX_TRANSFER_SCALING(value) (value)
inline constexpr int GX_TRANSFER_FMT_RGBA8 = 0, GX_TRANSFER_FMT_RGB8 = 1;
inline constexpr int GX_TRANSFER_SCALE_NO = 0, GFX_TOP = 0, GFX_LEFT = 0;
struct DVLE_s {};
struct DVLB_s {
    unsigned numDVLE{1};
    DVLE_s DVLE[1];
};
struct shaderInstance_s {};
struct shaderProgram_s {
    shaderInstance_s *vertexShader{nullptr};
};
DVLB_s *DVLB_ParseFile(u32 *, std::size_t);
void DVLB_Free(DVLB_s *);
Result shaderProgramInit(shaderProgram_s *);
Result shaderProgramSetVsh(shaderProgram_s *, DVLE_s *);
Result shaderProgramFree(shaderProgram_s *);
int shaderInstanceGetUniformLocation(shaderInstance_s *, const char *);
void *linearAlloc(std::size_t);
void linearFree(void *);
Result GSPGPU_FlushDataCache(const void *, std::size_t);
