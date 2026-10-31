#pragma once
#include "render_doubles/citro3d.h"
#include <array>
#include <string_view>
namespace room_sdk {
inline std::string_view failure;
inline unsigned active{}, frames{}, draws{}, begins{}, waits{}, hooks{}, unhooks{}, live_linear{},
    live_textures{};
inline std::size_t bytes{}, peak{};
// Optional test observer counts simultaneous CPU staging and GPU-double allocations.
inline void (*memory_changed)(){};
inline bool pending{}, open_frame{}, screens{};
inline bool new_model{true}, cpu_fast{};
inline unsigned speedups{}, speedup_disables{};
inline void (*callback)(APT_HookType, void *){};
inline void *context{};
inline int writes{}, alpha{}, cull{}, texture{-1};
inline bool blended{};
struct Draw {
    bool indexed{};
    int texture{}, first{}, count{};
};
inline std::array<Draw, 8192> draw_log{};
inline unsigned draw_count{}, indexed_draws{}, palette_uploads{};
inline std::uint64_t transparent_hash{}, map_hash{};
inline std::array<C3D_FVec, 96> uniforms{};
inline float max_skin_error{};
struct Input {
    u32 held{}, down{};
    std::uint64_t tick{};
    int event{-1};
    bool clear_failure{};
};
inline std::array<Input, 4096> script{};
inline unsigned length{}, cursor{};
inline Input current{};
void reset();
std::uint32_t dynamic_digest();
const void *static_data(std::size_t &size);
} // namespace room_sdk
