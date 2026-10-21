#include "material_state.hpp"
#include <citro3d.h>

namespace sh3::platform::ctr {
void bind_material_backdrop() noexcept {
    auto *env = C3D_GetTexEnv(0);
    C3D_TexEnvInit(env);
    C3D_TexEnvSrc(env, C3D_Both, GPU_PRIMARY_COLOR, GPU_PRIMARY_COLOR);
    C3D_TexEnvFunc(env, C3D_Both, GPU_REPLACE);
    C3D_AlphaBlend(GPU_BLEND_ADD, GPU_BLEND_ADD, GPU_ONE, GPU_ZERO, GPU_ONE, GPU_ZERO);
    C3D_DepthTest(true, GPU_GEQUAL, GPU_WRITE_ALL);
    C3D_CullFace(GPU_CULL_NONE);
}
void bind_captured_glass() noexcept {
    auto *env = C3D_GetTexEnv(0);
    C3D_TexEnvInit(env);
    // RGB already contains captured vertex illumination and constant black fog.
    C3D_TexEnvSrc(env, C3D_RGB, GPU_TEXTURE0, GPU_PRIMARY_COLOR);
    C3D_TexEnvSrc(env, C3D_Alpha, GPU_TEXTURE0, GPU_CONSTANT);
    C3D_TexEnvColor(env, 0xFDFFFFFF); // round(255 * 127/128), alpha in high byte.
    C3D_TexEnvFunc(env, C3D_Both, GPU_MODULATE);
    C3D_AlphaBlend(GPU_BLEND_ADD, GPU_BLEND_ADD, GPU_SRC_ALPHA, GPU_ONE_MINUS_SRC_ALPHA,
                   GPU_ONE, GPU_ZERO);
    C3D_DepthTest(true, GPU_GEQUAL, GPU_WRITE_COLOR); // GS ZMSK=1.
    C3D_CullFace(GPU_CULL_BACK_CCW);
}
} // namespace sh3::platform::ctr
