#include "check.hpp"
#include "room_material_state.hpp"
#include <citro3d.h>
#include <cstring>

namespace {
struct State {
    int source[2][2]{}, function[2]{}, alpha_enabled{}, alpha_mode{}, alpha_ref{}, depth{},
        depth_mode{}, write{}, cull{}, source_blend{}, destination_blend{};
    unsigned constant{};
} state;
C3D_TexEnv env;
} // namespace
C3D_TexEnv *C3D_GetTexEnv(int n) {
    CHECK(n == 0);
    return &env;
}
void C3D_TexEnvInit(C3D_TexEnv *) { state.source[0][0] = state.source[1][0] = -1; }
void C3D_TexEnvSrc(C3D_TexEnv *, int channels, int a, int b) {
    for (int i = 0; i < 2; ++i)
        if (channels & (1 << i)) {
            state.source[i][0] = a;
            state.source[i][1] = b;
        }
}
void C3D_TexEnvFunc(C3D_TexEnv *, int channels, int mode) {
    for (int i = 0; i < 2; ++i)
        if (channels & (1 << i))
            state.function[i] = mode;
}
void C3D_TexEnvColor(C3D_TexEnv *, u32 c) { state.constant = c; }
void C3D_AlphaTest(bool enabled, int mode, int ref) {
    state.alpha_enabled = enabled;
    state.alpha_mode = mode;
    state.alpha_ref = ref;
}
void C3D_DepthTest(bool enabled, int mode, int write) {
    state.depth = enabled;
    state.depth_mode = mode;
    state.write = write;
}
void C3D_AlphaBlend(GPU_BLENDEQUATION a, GPU_BLENDEQUATION b, GPU_BLENDFACTOR src,
                    GPU_BLENDFACTOR dst, GPU_BLENDFACTOR sa, GPU_BLENDFACTOR da) {
    CHECK(a == GPU_BLEND_ADD && b == GPU_BLEND_ADD && sa == GPU_ONE && da == GPU_ZERO);
    state.source_blend = src;
    state.destination_blend = dst;
}
void C3D_CullFace(int v) { state.cull = v; }
int main() {
    using P = sh3::domain::RoomPass;
    for (auto previous :
         {P::neutral, P::opaque, P::glass, P::hair, P::map_opaque, P::map_cutout, P::map_blend})
        for (auto next : {P::neutral, P::opaque, P::glass, P::hair, P::map_opaque, P::map_cutout,
                          P::map_blend}) {
            CHECK(sh3::platform::ctr::bind_room_material(previous));
            CHECK(sh3::platform::ctr::bind_room_material(next));
            CHECK(state.depth && state.depth_mode == GPU_GEQUAL);
            const bool blended = next == P::glass || next == P::hair || next == P::map_blend;
            CHECK(state.write ==
                  ((next == P::glass || next == P::hair) ? GPU_WRITE_COLOR : GPU_WRITE_ALL));
            CHECK(state.source_blend == (blended ? GPU_SRC_ALPHA : GPU_ONE));
            CHECK(state.destination_blend == (blended ? GPU_ONE_MINUS_SRC_ALPHA : GPU_ZERO));
            CHECK(state.cull == (next == P::glass ? GPU_CULL_BACK_CCW : GPU_CULL_NONE));
            CHECK(bool(state.alpha_enabled) ==
                  (next == P::opaque || next == P::hair || next == P::map_cutout));
            CHECK(state.alpha_ref == (next == P::hair ? 100 : 0));
            CHECK(state.source[0][0] == (next == P::neutral ? GPU_PRIMARY_COLOR : GPU_TEXTURE0));
            CHECK(state.function[0] == (next == P::neutral ? GPU_REPLACE : GPU_MODULATE));
            if (next == P::map_opaque)
                CHECK(state.source[1][1] == GPU_CONSTANT && state.constant == 0x00FFFFFF);
            if (next == P::glass || next == P::map_cutout || next == P::map_blend)
                CHECK(state.source[1][1] == GPU_CONSTANT && state.constant == 0xFDFFFFFF);
        }
    const auto before = state;
    CHECK(!sh3::platform::ctr::bind_room_material(static_cast<P>(99)));
    CHECK(std::memcmp(&before, &state, sizeof(state)) == 0);
}
