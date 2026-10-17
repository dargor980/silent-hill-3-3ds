#include "check.hpp"
#include "sh3/domain/diagnostic_options.hpp"
#include <limits>

int main() {
    using namespace sh3::domain;
    const OptionsBytes golden{0x53, 0x33, 0x4f, 0x50, 1,    1,    0,    0,
                              4,    3,    2,    1,    0x16, 0xf5, 0xb6, 0x54};
    CHECK(encode_options({{true}, 0x01020304}) == golden);
    OptionsRecord output{{false}, 99};
    CHECK(decode_options(golden.data(), golden.size(), output));
    CHECK(output.options.tone_enabled && output.generation == 0x01020304);
    for (bool enabled : {false, true}) {
        for (auto generation : {1U, 255U, 256U, std::numeric_limits<std::uint32_t>::max()}) {
            const auto bytes = encode_options({{enabled}, generation});
            CHECK(decode_options(bytes.data(), bytes.size(), output));
            CHECK(output.options.tone_enabled == enabled && output.generation == generation);
        }
    }
    // Every single byte altered, every truncation, and appended data are rejected.
    for (unsigned i = 0; i < golden.size(); ++i) {
        auto bytes = golden;
        bytes[i] ^= 0xff;
        output = {{false}, 99};
        CHECK(!decode_options(bytes.data(), bytes.size(), output));
        CHECK(!output.options.tone_enabled && output.generation == 99);
    }
    for (unsigned size = 0; size < golden.size(); ++size) {
        CHECK(!decode_options(golden.data(), size, output));
    }
    CHECK(!decode_options(golden.data(), 17, output));
    CHECK(!decode_options(nullptr, 16, output));
    const auto zero = encode_options({{true}, 0});
    CHECK(!decode_options(zero.data(), zero.size(), output));
}
