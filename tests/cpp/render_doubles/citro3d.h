#pragma once
float C3D_GetDrawingTime();
#include "3ds.h"

inline constexpr int C3D_DEFAULT_CMDBUF_SIZE = 0x40000, C3D_FRAME_SYNCDRAW = 1;
inline constexpr int GPU_RB_RGBA8 = 0, GPU_RB_DEPTH24_STENCIL8 = 1, GPU_RGBA8 = 2;
inline constexpr int GPU_NEAREST = 3, GPU_REPEAT = 4, GPU_FLOAT = 5, GPU_TEXTURE0 = 6;
inline constexpr int GPU_PRIMARY_COLOR = 7, GPU_MODULATE = 8, GPU_GREATER = 9;
inline constexpr int GPU_WRITE_ALL = 31, GPU_CULL_NONE = 10, GPU_TRIANGLES = 11;
inline constexpr int GPU_LINEAR = 12, GPU_CLAMP_TO_EDGE = 13, GPU_GEQUAL = 14;
inline constexpr int GPU_WRITE_COLOR = 15, GPU_CULL_BACK_CCW = 16, GPU_CONSTANT = 17;
inline constexpr int GPU_ALWAYS = 19;
inline constexpr int GPU_REPLACE = 18, C3D_RGB = 1, C3D_Alpha = 2;
inline constexpr int GPU_VERTEX_SHADER = 0, C3D_Both = 3, C3D_CLEAR_ALL = 3;
enum GPU_BLENDEQUATION { GPU_BLEND_ADD = 0 };
enum GPU_BLENDFACTOR { GPU_ZERO = 0, GPU_ONE = 1, GPU_SRC_ALPHA = 6, GPU_ONE_MINUS_SRC_ALPHA = 7 };
inline constexpr float C3D_AspectRatioTop = 400.0F / 240.0F;
struct C3D_RenderTarget {};
struct C3D_Mtx {
    float data[16]{};
};
struct C3D_FVec {
    float x, y, z;
};
struct C3D_Tex {
    void *data{nullptr};
};
struct C3D_AttrInfo {};
struct C3D_BufInfo {};
struct C3D_TexEnv {};
inline float C3D_AngleFromDegrees(float degrees) { return degrees * 0.01745329252F; }
inline C3D_FVec FVec3_New(float x, float y, float z) { return {x, y, z}; }
bool C3D_Init(std::size_t);
void C3D_Fini();
C3D_RenderTarget *C3D_RenderTargetCreate(int, int, int, int);
void C3D_RenderTargetSetOutput(C3D_RenderTarget *, int, int, u32);
void C3D_RenderTargetDelete(C3D_RenderTarget *);
void C3D_RenderTargetClear(C3D_RenderTarget *, int, u32, u32);
bool C3D_FrameBegin(int);
bool C3D_FrameDrawOn(C3D_RenderTarget *);
void C3D_FrameEnd(int);
bool C3D_TexInit(C3D_Tex *, unsigned, unsigned, int);
void C3D_TexDelete(C3D_Tex *);
void C3D_TexSetFilter(C3D_Tex *, int, int);
void C3D_TexSetWrap(C3D_Tex *, int, int);
void C3D_TexBind(int, C3D_Tex *);
C3D_AttrInfo *C3D_GetAttrInfo();
void AttrInfo_Init(C3D_AttrInfo *);
int AttrInfo_AddLoader(C3D_AttrInfo *, int, int, int);
C3D_BufInfo *C3D_GetBufInfo();
void C3D_SetBufInfo(C3D_BufInfo *);
void BufInfo_Init(C3D_BufInfo *);
int BufInfo_Add(C3D_BufInfo *, const void *, std::ptrdiff_t, int, std::uint64_t);
void Mtx_PerspTilt(C3D_Mtx *, float, float, float, float, bool);
void Mtx_LookAt(C3D_Mtx *, C3D_FVec, C3D_FVec, C3D_FVec, bool);
void Mtx_Multiply(C3D_Mtx *, const C3D_Mtx *, const C3D_Mtx *);
void C3D_FVUnifMtx4x4(int, int, const C3D_Mtx *);
void C3D_BindProgram(shaderProgram_s *);
C3D_TexEnv *C3D_GetTexEnv(int);
void C3D_TexEnvInit(C3D_TexEnv *);
void C3D_TexEnvSrc(C3D_TexEnv *, int, int, int);
void C3D_TexEnvFunc(C3D_TexEnv *, int, int);
void C3D_TexEnvColor(C3D_TexEnv *, u32);
void C3D_AlphaTest(bool, int, int);
void C3D_DepthTest(bool, int, int);
void C3D_AlphaBlend(GPU_BLENDEQUATION, GPU_BLENDEQUATION, GPU_BLENDFACTOR, GPU_BLENDFACTOR,
                    GPU_BLENDFACTOR, GPU_BLENDFACTOR);
void C3D_CullFace(int);
void C3D_DrawArrays(int, int, int);
