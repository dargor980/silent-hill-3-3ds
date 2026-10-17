#include "fixture.hpp"
#include <plutosvg.h>
#include <ft2build.h>
#include FT_FREETYPE_H
#include FT_MODULE_H

#ifndef PLUTOSVG_HAS_FREETYPE
#error The exported PlutoSVG target must include FreeType support
#endif

using Document = std::unique_ptr<plutosvg_document_t, Cleanup<plutosvg_document_destroy>>;
using Library = std::unique_ptr<FT_LibraryRec_, Cleanup<FT_Done_FreeType>>;
using Face = std::unique_ptr<FT_FaceRec_, Cleanup<FT_Done_Face>>;

static Document document(const std::vector<char>& data) {
    Document result(plutosvg_document_load_from_data(data.data(), static_cast<int>(data.size()),
                                                     -1, -1, nullptr, nullptr));
    require(bool(result), "parse own scene");
    require(plutosvg_document_get_width(result.get()) == 16 &&
            plutosvg_document_get_height(result.get()) == 12, "intrinsic dimensions");
    return result;
}

static void render(const std::vector<char>& data) {
    const auto doc = document(data);
    for (const int scale : {1, 2}) {
        const Surface surface(plutosvg_document_render_to_surface(doc.get(), nullptr,
            scale == 1 ? -1 : 32, -1, nullptr, nullptr, nullptr));
        dimensions(surface.get(), 16 * scale, 12 * scale);
        pixels(surface.get(), [scale](int x, int y) {
            if (x >= 2 * scale && x < 6 * scale && y >= 2 * scale && y < 5 * scale)
                return 0xffff0000u;
            if (x >= 8 * scale && x < 12 * scale && y >= 4 * scale && y < 8 * scale)
                return 0xff00ff00u;
            return 0u;
        });
    }
}

static void ids(const std::vector<char>& data) {
    const auto doc = document(data);
    plutovg_rect_t rect;
    require(plutosvg_document_extents(doc.get(), "red", &rect), "element extents");
    require(rect.x == 2 && rect.y == 2 && rect.w == 4 && rect.h == 3, "red bounds");
    const Surface surface(plutosvg_document_render_to_surface(doc.get(), "red", -1, -1,
                                                               nullptr, nullptr, nullptr));
    dimensions(surface.get(), 4, 3);
    pixels(surface.get(), [](int, int) { return 0xffff0000u; });
    require(!plutosvg_document_extents(doc.get(), "missing", &rect), "missing extents");
    const Surface missing(plutosvg_document_render_to_surface(doc.get(), "missing", 16, 12,
                                                               nullptr, nullptr, nullptr));
    require(!missing, "missing ID rejected");
}

static void invalid(const std::vector<char>& data) {
    for (const char* text : {"", "not svg", "<svg"}) {
        const Document bad(plutosvg_document_load_from_data(text, static_cast<int>(std::strlen(text)),
                                                             -1, -1, nullptr, nullptr));
        require(!bad, "invalid input rejected");
    }
    const auto doc = document(data);
    const Surface too_large(plutosvg_document_render_to_surface(doc.get(), nullptr, 32768, 1,
                                                                 nullptr, nullptr, nullptr));
    require(!too_large, "oversized target rejected before allocation");
}

static void freetype(const char* font_path) {
    const auto data = read_file(font_path);
    FT_Library raw = nullptr;
    require(FT_Init_FreeType(&raw) == 0, "init FreeType");
    const Library library(raw);
    int major, minor, patch;
    FT_Library_Version(raw, &major, &minor, &patch);
    require(major == 2 && minor == 14 && patch == 3, "FreeType binary version");
    // The fixed PCSX2 ImGui consumer uses this exported compatibility API too.
    const auto hooks = plutosvg_ft_svg_hooks();
    require(hooks != nullptr, "hooks exported by shared PlutoSVG");
    require(FT_Property_Set(raw, "ot-svg", "svg-hooks", hooks) == 0, "install SVG hooks");
    FT_Face raw_face = nullptr;
    require(FT_New_Memory_Face(raw, reinterpret_cast<const FT_Byte*>(data.data()),
                               static_cast<FT_Long>(data.size()), 0, &raw_face) == 0, "load SVG font");
    const Face face(raw_face);
    require(FT_HAS_SVG(raw_face) && FT_Get_Char_Index(raw_face, 'A') == 2, "own SVG glyph");
    for (const unsigned size : {50u, 100u, 50u}) {
        require(FT_Set_Pixel_Sizes(raw_face, 0, size) == 0, "SVG pixel size");
        require(FT_Load_Char(raw_face, 'A', FT_LOAD_COLOR | FT_LOAD_NO_HINTING) == 0,
                "load colored SVG glyph");
        require(raw_face->glyph->format == FT_GLYPH_FORMAT_SVG, "SVG path selected");
        require(FT_Render_Glyph(raw_face->glyph, FT_RENDER_MODE_NORMAL) == 0, "render SVG glyph");
        const auto slot = raw_face->glyph;
        const auto& bitmap = slot->bitmap;
        require(slot->format == FT_GLYPH_FORMAT_BITMAP && bitmap.pixel_mode == FT_PIXEL_MODE_BGRA,
                "BGRA raster result");
        require(bitmap.width == size * 4 / 10 && bitmap.rows == size * 7 / 10,
                "SVG raster dimensions");
        require(slot->bitmap_left == 0 && slot->bitmap_top == int(bitmap.rows), "SVG origin");
        require(slot->advance.x == FT_Pos(size * 600 * 64 / 1000) && slot->advance.y == 0,
                "SVG advance");
        require(bitmap.buffer && bitmap.pitch >= int(bitmap.width * 4), "BGRA storage");
        for (unsigned y = 0; y < bitmap.rows; ++y) {
            for (unsigned x = 0; x < bitmap.width; ++x) {
                const auto pixel = bitmap.buffer + y * bitmap.pitch + x * 4;
                require(pixel[0] == 0 && pixel[1] == 0 && pixel[2] == 255 && pixel[3] == 255,
                        "red SVG glyph pixel");
            }
        }
    }
}

int main(int argc, char** argv) try {
    require(argc == 4, "usage: fixture CASE SCENE FONT");
    require(plutosvg_version() == PLUTOSVG_VERSION &&
            std::string(plutosvg_version_string()) == "0.0.7" &&
            std::string(PLUTOSVG_VERSION_STRING) == "0.0.7", "SVG header/binary version");
    const auto data = read_file(argv[2]);
    const std::string test(argv[1]);
    if (test == "render") render(data);
    else if (test == "ids") ids(data);
    else if (test == "invalid") invalid(data);
    else if (test == "freetype") freetype(argv[3]);
    else throw std::runtime_error("unknown case");
    std::cout << "PASS " << test << '\n';
    return 0;
} catch (const std::exception& error) {
    std::cerr << error.what() << '\n';
    return 1;
}
