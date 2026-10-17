#include "fixture.hpp"

static void raster() {
    const Surface surface(plutovg_surface_create(16, 12));
    dimensions(surface.get(), 16, 12);
    require(plutovg_surface_get_stride(surface.get()) == 64, "owned stride");
    pixels(surface.get(), [](int, int) { return 0u; });
    const Canvas canvas(plutovg_canvas_create(surface.get()));
    require(bool(canvas), "canvas allocation");
    plutovg_canvas_set_rgb(canvas.get(), 1, 0, 0);
    plutovg_canvas_fill_rect(canvas.get(), 2, 3, 4, 5);
    pixels(surface.get(), [](int x, int y) {
        return x >= 2 && x < 6 && y >= 3 && y < 8 ? 0xffff0000u : 0u;
    });
}

static void composite() {
    const Surface surface(plutovg_surface_create(8, 8));
    dimensions(surface.get(), 8, 8);
    const Canvas canvas(plutovg_canvas_create(surface.get()));
    require(bool(canvas), "canvas allocation");
    plutovg_canvas_set_rgb(canvas.get(), 0, 0, 1);
    plutovg_canvas_fill_rect(canvas.get(), 0, 0, 8, 8);
    // 128/255 alpha gives integer premultiplied channels, avoiding half rounding.
    plutovg_canvas_set_rgba(canvas.get(), 1, 0, 0, 128.f / 255.f);
    plutovg_canvas_fill_rect(canvas.get(), 2, 2, 4, 4);
    pixels(surface.get(), [](int x, int y) {
        return x >= 2 && x < 6 && y >= 2 && y < 6 ? 0xff80007fu : 0xff0000ffu;
    });
    const Surface transparent(plutovg_surface_create(2, 2));
    dimensions(transparent.get(), 2, 2);
    const Canvas second(plutovg_canvas_create(transparent.get()));
    require(bool(second), "canvas allocation");
    plutovg_canvas_set_rgba(second.get(), 1, 0, 0, 128.f / 255.f);
    plutovg_canvas_fill_rect(second.get(), 0, 0, 2, 2);
    pixels(transparent.get(), [](int, int) { return 0x80800000u; });
}

static void guards() {
    constexpr std::uint32_t sentinel = 0xa55a5aa5u;
    constexpr int width = 8, height = 6, row_words = 12, guard_words = 4;
    std::vector<std::uint32_t> memory(guard_words * 2 + row_words * height, sentinel);
    for (int y = 0; y < height; ++y)
        for (int x = 0; x < width; ++x) memory[guard_words + y * row_words + x] = 0;
    {
        const Surface surface(plutovg_surface_create_for_data(
            reinterpret_cast<unsigned char*>(memory.data() + guard_words), width, height,
            row_words * 4));
        dimensions(surface.get(), width, height);
        require(plutovg_surface_get_stride(surface.get()) == row_words * 4, "external stride");
        const Canvas canvas(plutovg_canvas_create(surface.get()));
        require(bool(canvas), "canvas allocation");
        plutovg_canvas_clip_rect(canvas.get(), 1, 1, 4, 3);
        plutovg_canvas_translate(canvas.get(), 2, 0);
        plutovg_canvas_set_rgb(canvas.get(), 0, 1, 0);
        plutovg_canvas_fill_rect(canvas.get(), 0, -10, 20, 30);
        pixels(surface.get(), [](int x, int y) {
            return x >= 2 && x < 5 && y >= 1 && y < 4 ? 0xff00ff00u : 0u;
        });
    }
    for (int i = 0; i < guard_words; ++i) {
        require(memory[i] == sentinel && memory[memory.size() - 1 - i] == sentinel,
                "buffer guards preserved after destroy");
    }
    for (int y = 0; y < height; ++y)
        for (int x = width; x < row_words; ++x)
            require(memory[guard_words + y * row_words + x] == sentinel, "row padding preserved");
}

static void bounds() {
    for (const auto size : {0, -1, 32768}) {
        const Surface bad_width(plutovg_surface_create(size, 1));
        const Surface bad_height(plutovg_surface_create(1, size));
        require(!bad_width && !bad_height, "reject invalid owned dimensions");
    }
    const Surface single(plutovg_surface_create(1, 1));
    dimensions(single.get(), 1, 1);
    pixels(single.get(), [](int, int) { return 0u; });
    plutovg_matrix_t singular, inverse;
    plutovg_matrix_init_scale(&singular, 0, 1);
    require(!plutovg_matrix_invert(&singular, &inverse), "reject singular inverse");
}

int main(int argc, char** argv) try {
    require(argc == 2, "usage: fixture CASE");
    require(plutovg_version() == PLUTOVG_VERSION &&
            std::string(plutovg_version_string()) == "1.3.2" &&
            std::string(PLUTOVG_VERSION_STRING) == "1.3.2", "VG header/binary version");
    const std::string test(argv[1]);
    if (test == "raster") raster();
    else if (test == "composite") composite();
    else if (test == "guards") guards();
    else if (test == "bounds") bounds();
    else throw std::runtime_error("unknown case");
    std::cout << "PASS " << test << '\n';
    return 0;
} catch (const std::exception& error) {
    std::cerr << error.what() << '\n';
    return 1;
}
