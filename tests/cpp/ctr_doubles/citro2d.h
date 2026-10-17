#pragma once

#include <3ds.h>
#include <cstddef>

struct C3D_RenderTarget {};
inline constexpr std::size_t C3D_DEFAULT_CMDBUF_SIZE = 0x40000;
inline constexpr std::size_t C2D_DEFAULT_MAX_OBJECTS = 4096;
inline constexpr u8 C3D_FRAME_SYNCDRAW = 1;

bool C3D_Init(std::size_t size);
void C3D_Fini();
bool C2D_Init(std::size_t objects);
void C2D_Fini();
void C2D_Prepare();
C3D_RenderTarget *C2D_CreateScreenTarget(gfxScreen_t screen, gfx3dSide_t side);
void C3D_RenderTargetDelete(C3D_RenderTarget *target);
bool C3D_FrameBegin(u8 flags);
void C3D_FrameEnd(u8 flags);
void C2D_TargetClear(C3D_RenderTarget *target, u32 color);
void C2D_SceneBegin(C3D_RenderTarget *target);
bool C2D_DrawRectSolid(float x, float y, float z, float width, float height, u32 color);
constexpr u32 C2D_Color32(u8 r, u8 g, u8 b, u8 a) {
    return u32{r} | (u32{g} << 8U) | (u32{b} << 16U) | (u32{a} << 24U);
}
