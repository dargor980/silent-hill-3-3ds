#include <hb.h>
#include <hb-ot.h>

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
    template<class T> void operator()(T* p) const { if (p) destroy(p); }
};
using Blob = std::unique_ptr<hb_blob_t, Cleanup<hb_blob_destroy>>;
using Face = std::unique_ptr<hb_face_t, Cleanup<hb_face_destroy>>;
using Font = std::unique_ptr<hb_font_t, Cleanup<hb_font_destroy>>;
using Buffer = std::unique_ptr<hb_buffer_t, Cleanup<hb_buffer_destroy>>;
struct Expected { unsigned glyph, cluster; int advance; };

static void shape(hb_font_t* font, const char* text,
                  const std::vector<hb_feature_t>& features,
                  const std::vector<Expected>& expected) {
    const Buffer buffer(hb_buffer_create());
    hb_buffer_add_utf8(buffer.get(), text, -1, 0, -1);
    hb_buffer_set_direction(buffer.get(), HB_DIRECTION_LTR);
    hb_buffer_set_script(buffer.get(), HB_SCRIPT_LATIN);
    hb_buffer_set_language(buffer.get(), hb_language_from_string("es", -1));
    require(hb_buffer_allocation_successful(buffer.get()), "buffer allocation");
    const char* shapers[] = {"ot", nullptr};
    require(hb_shape_full(font, buffer.get(), features.data(),
                          static_cast<unsigned>(features.size()), shapers), "OpenType shaping");
    unsigned count = 0, positions_count = 0;
    const auto info = hb_buffer_get_glyph_infos(buffer.get(), &count);
    const auto pos = hb_buffer_get_glyph_positions(buffer.get(), &positions_count);
    require(count == expected.size() && count == positions_count, "glyph count");
    for (unsigned i = 0; i < count; ++i) {
        require(info[i].codepoint == expected[i].glyph, "glyph ID");
        require(info[i].cluster == expected[i].cluster, "cluster");
        require(pos[i].x_advance == expected[i].advance && pos[i].y_advance == 0,
                "advance");
        require(pos[i].x_offset == 0 && pos[i].y_offset == 0, "offset");
    }
}

int main(int argc, char** argv) try {
    require(argc == 3, "usage: fixture CASE FONT");
    std::ifstream input(argv[2], std::ios::binary);
    require(input.good(), "font readable");
    const std::vector<char> data{std::istreambuf_iterator<char>(input), {}};
    require(data.size() > 12 && data.size() < 65536, "bounded fixture");
    require(std::string(hb_version_string()) == "14.2.0" &&
            std::string(HB_VERSION_STRING) == "14.2.0", "header/binary version");
    const Blob blob(hb_blob_create(data.data(), static_cast<unsigned>(data.size()),
                                  HB_MEMORY_MODE_READONLY, nullptr, nullptr));
    const Face face(hb_face_create(blob.get(), 0));
    require(hb_face_get_upem(face.get()) == 1000 && hb_face_get_glyph_count(face.get()) == 5,
            "font dimensions");
    const Font font(hb_font_create(face.get()));
    hb_ot_font_set_funcs(font.get());
    hb_font_set_scale(font.get(), 1000, 1000);
    const std::string test(argv[1]);
    if (test == "shape") {
        shape(font.get(), "AVA", {}, {{4, 0, 1000}, {2, 2, 600}});
        shape(font.get(), "A V", {}, {{2, 0, 600}, {1, 1, 250}, {3, 2, 650}});
    } else if (test == "features") {
        hb_feature_t liga_off, kern_off;
        require(hb_feature_from_string("liga=0", -1, &liga_off), "parse liga feature");
        require(hb_feature_from_string("kern=0", -1, &kern_off), "parse kern feature");
        shape(font.get(), "AVA", {liga_off, kern_off}, {{2, 0, 600}, {3, 1, 650}, {2, 2, 600}});
        shape(font.get(), "AVA", {liga_off}, {{2, 0, 520}, {3, 1, 650}, {2, 2, 600}});
    } else if (test == "bounds") {
        shape(font.get(), "", {}, {});
        shape(font.get(), "\xf4\x8f\xbf\xbf", {}, {{0, 0, 500}});
        const Blob small(hb_blob_create(data.data(), 12, HB_MEMORY_MODE_READONLY, nullptr, nullptr));
        const Face invalid(hb_face_create(small.get(), 0));
        require(hb_face_get_glyph_count(invalid.get()) == 0, "truncated font has no glyphs");
    } else throw std::runtime_error("unknown case");
    std::cout << "PASS " << test << '\n';
    return 0;
} catch (const std::exception& error) {
    std::cerr << error.what() << '\n';
    return 1;
}
