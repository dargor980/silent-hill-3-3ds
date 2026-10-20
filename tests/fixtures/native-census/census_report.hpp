#pragma once
namespace sh3::observer::probe {
// Private candidate only. Captures metadata after CPU stop, before process exit.
void dump_image_census(const char* phase) noexcept;
}
