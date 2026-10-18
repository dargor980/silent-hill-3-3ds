// Separate libwebp producer/reader: no Qt dependencies.
#include "pattern.hpp"
#include <webp/decode.h>
#include <webp/encode.h>
#include <algorithm>
#include <filesystem>
#include <fstream>
#include <iterator>
#include <memory>
#include <string>
#include <vector>

using Bytes = std::vector<std::uint8_t>;
using OwnedWebp = std::unique_ptr<std::uint8_t, decltype(&WebPFree)>;
static void write(const std::filesystem::path& path, const Bytes& bytes) {
    std::ofstream stream(path, std::ios::binary);
    stream.write(reinterpret_cast<const char*>(bytes.data()), static_cast<std::streamsize>(bytes.size()));
    require(bool(stream), "Could not write fixture");
}
static void verify(const Bytes& bytes) {
    int w = 0, h = 0;
    OwnedWebp raw(WebPDecodeRGBA(bytes.data(), bytes.size(), &w, &h), WebPFree);
    require(raw != nullptr && w == width && h == height, "Independent WebP decode failed");
    for (int y = 0; y < height; ++y) for (int x = 0; x < width; ++x) {
        const auto color = expected(x, y);
        require(std::equal(color.begin(), color.end(), raw.get() + (y * width + x) * 4),
                "Independent WebP pixel mismatch");
    }
}
static Bytes tga(bool top) {
    Bytes out(18, 0); out[2] = 2; out[12] = width; out[14] = height;
    out[16] = 32; out[17] = top ? 0x28 : 0x08;
    for (int row = 0; row < height; ++row) for (int x = 0; x < width; ++x) {
        const auto c = expected(x, top ? row : height - row - 1);
        out.insert(out.end(), {c[2], c[1], c[0], c[3]});
    }
    out.insert(out.end(), 8, 0);
    const std::string signature = "TRUEVISION-XFILE.";
    out.insert(out.end(), signature.begin(), signature.end()); out.push_back(0);
    return out;
}
static void u16(Bytes& out, unsigned value) {
    out.push_back(value & 255); out.push_back((value >> 8) & 255);
}
static void u32(Bytes& out, unsigned value) { u16(out, value & 65535); u16(out, value >> 16); }
static Bytes tiff() {
    // Baseline little-endian TIFF: one uncompressed 3x2 gray strip, no external encoder.
    Bytes out{'I','I',42,0,8,0,0,0}; u16(out, 9);
    auto tag = [&](unsigned id, unsigned type, unsigned value) {
        u16(out, id); u16(out, type); u32(out, 1); u32(out, value);
    };
    tag(256,4,3); tag(257,4,2); tag(258,3,8); tag(259,3,1); tag(262,3,1);
    tag(273,4,122); tag(277,3,1); tag(278,4,2); tag(279,4,6); u32(out,0);
    require(out.size() == 122, "Incorrect TIFF pixel offset");
    out.insert(out.end(), {0,127,255,255,63,0}); return out;
}
int main(int argc, char** argv) {
    return checked([&] {
        require(argc == 3, "Expected generate directory or verify WebP file");
        const std::string mode = argv[1]; const std::filesystem::path path = argv[2];
        if (mode == "verify") {
            std::ifstream stream(path, std::ios::binary); require(bool(stream), "Missing WebP output");
            Bytes bytes{std::istreambuf_iterator<char>(stream), std::istreambuf_iterator<char>()};
            verify(bytes); return;
        }
        require(mode == "generate", "Unknown oracle command");
        std::filesystem::create_directories(path);
        Bytes pixels;
        for (int y = 0; y < height; ++y) for (int x = 0; x < width; ++x) {
            const auto color = expected(x,y); pixels.insert(pixels.end(), color.begin(), color.end());
        }
        std::uint8_t* raw = nullptr;
        const auto count = WebPEncodeLosslessRGBA(pixels.data(), width, height, width * 4, &raw);
        OwnedWebp owned(raw, WebPFree); require(count && owned, "WebP encoding failed");
        Bytes bytes(raw, raw + count); verify(bytes); write(path / "scene.webp", bytes);
        require(bytes.size() > 20, "WebP unexpectedly small");
        write(path / "bad.webp", Bytes(bytes.begin(), bytes.begin()+20));
        bytes = tga(true); write(path / "top.tga", bytes);
        write(path / "bad.tga", Bytes(bytes.begin(), bytes.begin()+9));
        write(path / "bottom.tga", tga(false));
        bytes = {0,0,9,3,0x55,0x7f,0xaa,0xff,0x55,0x7f};
        write(path / "scene.wbmp", bytes);
        write(path / "bad.wbmp", Bytes(bytes.begin(), bytes.end()-1));
        bytes = tiff(); write(path / "scene.tiff", bytes);
        write(path / "bad.tiff", Bytes(bytes.begin(), bytes.begin()+7));
    });
}
