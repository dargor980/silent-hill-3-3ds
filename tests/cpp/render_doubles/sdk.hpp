#pragma once
#include <string>
#include <vector>

namespace render_sdk {
inline std::string failure;
inline std::vector<std::string> events;
inline int acquired = 0, released = 0, allocations = 0, draws = 0, frames = 0;
inline bool pending = false, open_frame = false;
inline bool inspection = false, geometry = false;
inline bool material = false;
inline bool dynamic = false;
inline bool character = false, character_material = false;
inline bool rig = false;
inline float expected_focus[3]{0, .75F, -2};
inline std::vector<std::pair<unsigned, unsigned>> rig_dimensions;
inline unsigned character_instances = 1;
inline int texture_attempts = 0, texture_flushes = 0;
inline std::vector<unsigned char> expected_vertices;
} // namespace render_sdk
