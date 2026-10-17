#include <ft2build.h>
#include FT_FREETYPE_H

#include <fstream>
#include <iostream>
#include <iterator>
#include <memory>
#include <stdexcept>
#include <string>
#include <vector>

static void require(bool condition, const char* message) {
    if (!condition) throw std::runtime_error(message);
}
template<auto destroy> struct Cleanup {
    template<class T> void operator()(T* p) const { if (p) (void)destroy(p); }
};
using Library = std::unique_ptr<FT_LibraryRec_, Cleanup<FT_Done_FreeType>>;
using Face = std::unique_ptr<FT_FaceRec_, Cleanup<FT_Done_Face>>;

static void raster(FT_Face face) {
    require(face->units_per_EM == 1000 && face->num_glyphs == 5, "font dimensions");
    require(FT_Get_Char_Index(face, 'A') == 2 && FT_Get_Char_Index(face, 'V') == 3,
            "Unicode map");
    require(FT_Get_Char_Index(face, 0x10ffff) == 0, "missing glyph");
    for (const unsigned size : {50u, 100u}) {
        require(FT_Set_Pixel_Sizes(face, 0, size) == 0, "pixel size");
        require(FT_Load_Char(face, 'A', FT_LOAD_RENDER | FT_LOAD_NO_HINTING |
                            FT_LOAD_NO_AUTOHINT) == 0, "load and render");
        const auto glyph = face->glyph;
        const auto& bitmap = glyph->bitmap;
        require(bitmap.pixel_mode == FT_PIXEL_MODE_GRAY && bitmap.num_grays == 256,
                "gray raster format");
        require(bitmap.width == size * 4 / 10 && bitmap.rows == size * 7 / 10,
                "rectangle dimensions");
        require(glyph->bitmap_left == 0 && glyph->bitmap_top == int(bitmap.rows),
                "rectangle origin");
        require(glyph->advance.x == FT_Pos(size * 600 * 64 / 1000) &&
                glyph->advance.y == 0, "advance");
        require(bitmap.pitch >= int(bitmap.width) && bitmap.buffer, "raster storage");
        for (unsigned y = 0; y < bitmap.rows; ++y)
            for (unsigned x = 0; x < bitmap.width; ++x)
                require(bitmap.buffer[y * bitmap.pitch + x] == 255, "rectangle pixel");
    }
}

int main(int argc, char** argv) try {
    require(argc == 3, "usage: fixture CASE FONT");
    std::ifstream input(argv[2], std::ios::binary);
    require(input.good(), "font readable");
    const std::vector<unsigned char> data{std::istreambuf_iterator<char>(input), {}};
    require(data.size() > 12 && data.size() < 65536, "bounded fixture");
    FT_Library raw = nullptr;
    require(FT_Init_FreeType(&raw) == 0, "init FreeType");
    const Library library(raw);
    FT_Face raw_face = nullptr;
    require(FT_New_Memory_Face(raw, data.data(), static_cast<FT_Long>(data.size()),
                               0, &raw_face) == 0, "load font");
    const Face owner(raw_face);
    const std::string test(argv[1]);
    if (test == "version") {
        int major, minor, patch;
        FT_Library_Version(raw, &major, &minor, &patch);
        require(major == 2 && minor == 14 && patch == 3, "binary version");
        require(major == FREETYPE_MAJOR && minor == FREETYPE_MINOR &&
                patch == FREETYPE_PATCH, "header/binary version");
    } else if (test == "raster") {
        raster(raw_face);
    } else if (test == "autohint") {
        require(FT_Set_Pixel_Sizes(raw_face, 0, 50) == 0, "pixel size");
        require(FT_Load_Glyph(raw_face, 4, FT_LOAD_FORCE_AUTOHINT | FT_LOAD_RENDER) == 0,
                "auto-hinted ligature load");
        require(raw_face->glyph->bitmap.width > 0 && raw_face->glyph->bitmap.rows > 0,
                "auto-hinted bitmap");
        require(raw_face->glyph->advance.x == 50 * 64, "auto-hinted advance");
    } else if (test == "invalid") {
        FT_Face invalid = nullptr;
        auto status = FT_New_Memory_Face(raw, data.data(), 12, 0, &invalid);
        const Face truncated(invalid);
        require(status != 0 && invalid == nullptr, "reject truncated font");
        invalid = nullptr;
        status = FT_New_Memory_Face(raw, data.data(), static_cast<FT_Long>(data.size()),
                                    1, &invalid);
        const Face bad_index(invalid);
        require(status != 0 && invalid == nullptr, "reject invalid face index");
        require(FT_Load_Glyph(raw_face, 5, FT_LOAD_DEFAULT) != 0, "reject invalid glyph");
    } else throw std::runtime_error("unknown case");
    std::cout << "PASS " << test << '\n';
    return 0;
} catch (const std::exception& error) {
    std::cerr << error.what() << '\n';
    return 1;
}
