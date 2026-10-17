#pragma once
#include <plutovg.h>

#include <cstdint>
#include <cstring>
#include <fstream>
#include <iostream>
#include <iterator>
#include <memory>
#include <stdexcept>
#include <string>
#include <vector>

inline void require(bool condition, const char* message) {
    if (!condition) throw std::runtime_error(message);
}
template<auto destroy> struct Cleanup {
    template<class T> void operator()(T* p) const { if (p) (void)destroy(p); }
};
using Surface = std::unique_ptr<plutovg_surface_t, Cleanup<plutovg_surface_destroy>>;
using Canvas = std::unique_ptr<plutovg_canvas_t, Cleanup<plutovg_canvas_destroy>>;

inline std::vector<char> read_file(const char* path) {
    std::ifstream stream(path, std::ios::binary);
    require(stream.good(), "input readable");
    std::vector<char> data{std::istreambuf_iterator<char>(stream), {}};
    require(!data.empty() && data.size() < 65536, "bounded own input");
    return data;
}

inline void dimensions(plutovg_surface_t* surface, int width, int height) {
    require(surface != nullptr, "surface allocation");
    require(plutovg_surface_get_width(surface) == width &&
            plutovg_surface_get_height(surface) == height, "surface dimensions");
    require(plutovg_surface_get_stride(surface) >= width * 4, "surface stride");
}

template<class Expected> void pixels(plutovg_surface_t* surface, Expected expected) {
    const auto data = plutovg_surface_get_data(surface);
    const int stride = plutovg_surface_get_stride(surface);
    require(data != nullptr, "surface pixels");
    for (int y = 0; y < plutovg_surface_get_height(surface); ++y) {
        for (int x = 0; x < plutovg_surface_get_width(surface); ++x) {
            std::uint32_t actual;
            std::memcpy(&actual, data + y * stride + x * 4, 4);
            const std::uint32_t wanted = expected(x, y);
            if (actual != wanted) {
                std::cerr << "pixel(" << x << ',' << y << ") actual=" << std::hex
                          << actual << " expected=" << wanted << std::dec << '\n';
                throw std::runtime_error("pixel mismatch");
            }
        }
    }
}
