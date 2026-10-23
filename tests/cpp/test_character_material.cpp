#include "check.hpp"
#include "sh3/platform/inspection_character_material.hpp"
#include <cstring>
#include <memory>
#include <vector>
int main(int argc, char **argv) {
    using namespace sh3;
    auto data = std::make_unique<platform::CharacterMaterialData>();
    if (argc >= 2) {
        auto api = platform::system_stdio;
        if (argc == 3 && std::strcmp(argv[2], "close") == 0)
            api.close = +[](FILE *f) { std::fclose(f); return -1; };
        if (argc == 3 && std::strcmp(argv[2], "read") == 0)
            api.error = +[](FILE *) { return 1; };
        const auto result = platform::read_character_material(argv[1], *data, 0x12345678, 9, api);
        if (result != ports::FileError::ok) { CHECK(data->ranges[0].count == 0); return 2; }
        CHECK(data->ranges[2].first == 6);
        return 0;
    }
    CHECK(platform::read_character_material(nullptr, *data, 0, 9) == ports::FileError::invalid_target);
    CHECK(platform::read_character_material("/nonexistent/material.sct", *data, 0, 9) == ports::FileError::missing);
    domain::CharacterMaterials ranges{{{0,3,0}, {3,3,1}, {6,3,2}}};
    CHECK(domain::valid_character_materials(ranges, 9));
    CHECK(!domain::valid_character_materials(ranges, 8));
    CHECK(!domain::valid_character_materials(ranges, 12));
    ranges[1].first = 0;
    CHECK(!domain::valid_character_materials(ranges, 9));
    ranges[1] = {3, 0xffffffffU, 1};
    CHECK(!domain::valid_character_materials(ranges, 9));
    const auto size = platform::character_texture_bytes;
    std::vector<std::uint8_t> source(size), output(size, 0xFF);
    for (std::size_t y=0; y<512; ++y) for (std::size_t x=0; x<512; ++x) {
        const auto p = (y*512+x)*4;
        source[p] = x%256; source[p+1] = y%256; source[p+2] = (x+y)%256;
        source[p+3] = (x+y)%129;
    }
    CHECK(platform::upload_character_texture(source.data(), size, output.data(), size));
    // Independent decode of every Morton texel; asymmetry detects transposition/V reversal.
    for (std::size_t block=0; block<4096; ++block) for (std::size_t k=0; k<64; ++k) {
        const auto x = (block%64)*8 + (k&1) + ((k>>1)&2) + ((k>>2)&4);
        const auto y = (block/64)*8 + ((k>>1)&1) + ((k>>2)&2) + ((k>>3)&4);
        const auto src = (y*512+x)*4, dst = (block*64+k)*4;
        CHECK(output[dst] == (unsigned(source[src+3])*255+64)/128);
        CHECK(output[dst+1] == source[src+2] && output[dst+2] == source[src+1] && output[dst+3] == source[src]);
    }
    CHECK(!platform::upload_character_texture(nullptr, size, output.data(), size));
    CHECK(!platform::upload_character_texture(source.data(), size-1, output.data(), size));
    CHECK(!platform::upload_character_texture(source.data(), size, output.data(), size-1));
    CHECK(!platform::upload_character_texture(source.data(), size, source.data(), size));
    CHECK(!platform::upload_character_texture(source.data(), size, source.data()+4, size));
    source[3] = 129;
    CHECK(!platform::upload_character_texture(source.data(), size, output.data(), size));
}
