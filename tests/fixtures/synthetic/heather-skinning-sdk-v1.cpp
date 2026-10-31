// Compile-only HS-T2 layout contract against the pinned, real ARM SDK.
#include <citro3d.h>
#include <cstddef>
struct HsVertex {
    float position[4], weights[4], rows[4], uv[4];
};
static_assert(C3D_FVUNIF_COUNT == 96 && C3D_IVUNIF_COUNT == 4);
static_assert(sizeof(C3D_FVec) == 16 && sizeof(C3D_Mtx) == 64);
static_assert(offsetof(C3D_FVec, w) == 0 && offsetof(C3D_FVec, z) == 4);
static_assert(offsetof(C3D_FVec, y) == 8 && offsetof(C3D_FVec, x) == 12);
static_assert(sizeof(HsVertex) == 64 && alignof(HsVertex) == 4);
static_assert(offsetof(HsVertex, weights) == 16 && offsetof(HsVertex, rows) == 32);
static_assert(offsetof(HsVertex, uv) == 48);
static_assert(sizeof(C3D_BufInfo::buffers) / sizeof(C3D_BufCfg) == 12);
static_assert(C3D_UNSIGNED_SHORT == 1 && GPU_FLOAT == 3);
static_assert(30 * 3 + 4 + 1 == 95 && 31 * 3 + 4 + 1 > C3D_FVUNIF_COUNT);
// Emission permits auditing the memory order without running an ARM object.
extern "C" const C3D_FVec hs_order = {{4.0f, 3.0f, 2.0f, 1.0f}};
