#pragma once

namespace sh3::platform::ctr {
// No ownership or I/O. Called explicitly before each of the two draw passes.
void bind_character_material() noexcept;
void bind_material_backdrop() noexcept;
void bind_captured_glass() noexcept;
} // namespace sh3::platform::ctr
