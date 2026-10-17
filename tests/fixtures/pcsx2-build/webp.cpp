// Own opaque RGBA images; no original game textures or external image fixtures.
#include <webp/decode.h>
#include <webp/encode.h>

#include <algorithm>
#include <cstdint>
#include <iostream>
#include <memory>
#include <utility>
#include <vector>

int main() {
    for (const auto [width, height] : {std::pair{1, 1}, {17, 9}, {64, 64}}) {
        std::vector<std::uint8_t> pixels(width * height * 4);
        for (std::size_t i = 0; i < pixels.size(); i += 4) {
            pixels[i] = static_cast<std::uint8_t>(i * 17);
            pixels[i + 1] = static_cast<std::uint8_t>(i / 4);
            pixels[i + 2] = static_cast<std::uint8_t>(i / 7);
            pixels[i + 3] = 255;
        }
        std::uint8_t* raw = nullptr;
        const auto size = WebPEncodeLosslessRGBA(pixels.data(), width, height, width * 4, &raw);
        std::unique_ptr<std::uint8_t, decltype(&WebPFree)> encoded(raw, WebPFree);
        if (!size || !encoded) return 1;
        int decoded_width = 0, decoded_height = 0;
        std::unique_ptr<std::uint8_t, decltype(&WebPFree)> decoded(
            WebPDecodeRGBA(encoded.get(), size, &decoded_width, &decoded_height), WebPFree);
        if (!decoded || decoded_width != width || decoded_height != height) return 2;
        if (!std::equal(pixels.begin(), pixels.end(), decoded.get())) return 3;
        if (WebPDecodeRGBAInto(encoded.get(), size, pixels.data(), pixels.size() - 1, width * 4)) return 4;
        std::unique_ptr<std::uint8_t, decltype(&WebPFree)> truncated(
            WebPDecodeRGBA(encoded.get(), 4, &decoded_width, &decoded_height), WebPFree);
        if (truncated) return 5;
    }
    std::cout << "WebP: 3 lossless RGBA round trips; truncation and output bounds passed\n";
}
