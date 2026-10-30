#include "room_material_state.hpp"
#include "material_state.hpp"
#include <citro3d.h>

namespace sh3::platform::ctr {
bool bind_room_material(domain::RoomPass pass) noexcept {
    switch (pass) {
    case domain::RoomPass::neutral:
        bind_material_backdrop();
        C3D_AlphaTest(false, GPU_ALWAYS, 0);
        return true;
    case domain::RoomPass::opaque:
        bind_character_material();
        C3D_AlphaTest(true, GPU_GREATER, 0);
        return true;
    case domain::RoomPass::glass:
        bind_captured_glass();
        C3D_AlphaTest(false, GPU_ALWAYS, 0);
        return true;
    case domain::RoomPass::hair:
        bind_character_material();
        C3D_AlphaTest(true, GPU_GREATER, 100);
        C3D_AlphaBlend(GPU_BLEND_ADD, GPU_BLEND_ADD, GPU_SRC_ALPHA, GPU_ONE_MINUS_SRC_ALPHA,
                       GPU_ONE, GPU_ZERO);
        C3D_DepthTest(true, GPU_GEQUAL, GPU_WRITE_COLOR);
        return true;
    case domain::RoomPass::map_opaque:
    case domain::RoomPass::map_cutout:
    case domain::RoomPass::map_blend: {
        bind_character_material();
        auto *env = C3D_GetTexEnv(0);
        C3D_TexEnvSrc(env, C3D_Alpha, GPU_TEXTURE0, GPU_CONSTANT);
        C3D_TexEnvColor(env, pass == domain::RoomPass::map_opaque ? 0x00FFFFFF : 0xFDFFFFFF);
        C3D_AlphaTest(pass == domain::RoomPass::map_cutout,
                      pass == domain::RoomPass::map_cutout ? GPU_GREATER : GPU_ALWAYS, 0);
        if (pass == domain::RoomPass::map_blend)
            C3D_AlphaBlend(GPU_BLEND_ADD, GPU_BLEND_ADD, GPU_SRC_ALPHA, GPU_ONE_MINUS_SRC_ALPHA,
                           GPU_ONE, GPU_ZERO);
        return true;
    }
    default:
        return false;
    }
}
} // namespace sh3::platform::ctr
