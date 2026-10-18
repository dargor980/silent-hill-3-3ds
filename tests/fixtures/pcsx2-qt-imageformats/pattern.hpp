#pragma once
#include <array>
#include <cstdint>
#include <iostream>
#include <stdexcept>

inline constexpr int width = 32;
inline constexpr int height = 24;
using Pixel = std::array<std::uint8_t, 4>;
inline Pixel expected(int x, int y) {
    if (y < height / 2) return x < width / 2 ? Pixel{224, 32, 48, 255} : Pixel{32, 64, 224, 128};
    return x < width / 2 ? Pixel{16, 160, 48, 255} : Pixel{0, 0, 0, 0};
}
inline void require(bool value, const char* message) {
    if (!value) throw std::runtime_error(message);
}
template<class Function> int checked(Function action) {
    try { action(); std::cout << "PASS\n"; return 0; }
    catch (const std::exception& error) { std::cerr << error.what() << '\n'; return 1; }
}
