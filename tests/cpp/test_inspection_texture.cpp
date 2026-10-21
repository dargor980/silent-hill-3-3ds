#include "check.hpp"
#include "sh3/platform/inspection_crc32.hpp"
#include "sh3/platform/inspection_texture.hpp"
#include <algorithm>
#include <array>
#include <cerrno>
#include <cstring>
#include <string>
#include <vector>

namespace {
using namespace sh3::platform;
using E = sh3::ports::FileError;
std::vector<std::uint8_t> input;
std::size_t cursor = 0, reads = 0, closes = 0;
std::string fault;
bool io_error = false;
std::FILE *open_file(const char *, const char *mode) {
    CHECK(std::strcmp(mode, "rb") == 0);
    if (fault == "missing" || fault == "open") {
        errno = fault == "missing" ? ENOENT : EACCES;
        return nullptr;
    }
    return reinterpret_cast<std::FILE *>(1);
}
std::size_t read_file(void *destination, std::size_t unit, std::size_t size, std::FILE *) {
    CHECK(unit == 1);
    ++reads;
    if (fault == "read" + std::to_string(reads)) {
        io_error = true;
        return 0;
    }
    const auto count = std::min(size, input.size() - cursor);
    std::copy_n(input.data() + cursor, count, static_cast<std::uint8_t *>(destination));
    cursor += count;
    return count;
}
int error_file(std::FILE *) noexcept { return io_error ? 1 : 0; }
int close_file(std::FILE *) {
    ++closes;
    return fault == "close" ? -1 : 0;
}
const StdioApi api{open_file, read_file, nullptr, error_file, nullptr, close_file};
std::vector<std::uint8_t> pattern() {
    std::vector<std::uint8_t> bytes(inspection_bytes);
    for (unsigned y = 0; y < 256; ++y) {
        for (unsigned x = 0; x < 256; ++x) {
            const auto i = (y * 256 + x) * 4;
            bytes[i] = x;
            bytes[i + 1] = y;
            bytes[i + 2] = x ^ y;
            bytes[i + 3] = 255;
        }
    }
    return bytes;
}
void put(std::size_t offset, std::uint32_t value) {
    for (unsigned i = 0; i < 4; ++i)
        input[offset + i] = value >> (i * 8);
}
} // namespace

int main(int argc, char **argv) {
    const auto rgba = pattern();
    std::vector<std::uint8_t> output(inspection_bytes + 2, 0xA5);
    if (argc == 2) {
        const auto result = read_inspection_texture(argv[1], output.data(), inspection_bytes);
        if (result != E::ok)
            return 2;
        CHECK(std::equal(rgba.begin(), rgba.end(), output.begin()));
        return 0;
    }
    const auto *text = reinterpret_cast<const std::uint8_t *>("123456789");
    CHECK(inspection_crc32(text, 9) == 0xCBF43926);
    CHECK(inspection_crc32(text, 0) == 0);
    CHECK(
        upload_inspection_pixels({rgba.data(), rgba.size()}, output.data() + 1, inspection_bytes));
    CHECK(output.front() == 0xA5 && output.back() == 0xA5);
    // Inverse oracle: enumerate physical tiles and de-interleave Morton bits.
    for (unsigned tile = 0; tile < 1024; ++tile) {
        for (unsigned m = 0; m < 64; ++m) {
            unsigned x = (tile % 32) * 8, y = (tile / 32) * 8;
            for (unsigned bit = 0; bit < 3; ++bit) {
                x += ((m >> (2 * bit)) & 1) << bit;
                y += ((m >> (2 * bit + 1)) & 1) << bit;
            }
            const auto source = (y * 256 + x) * 4;
            const auto target = 1 + (tile * 64 + m) * 4;
            for (unsigned c = 0; c < 4; ++c)
                CHECK(output[target + c] == rgba[source + 3 - c]);
        }
    }
    CHECK(!upload_inspection_pixels({nullptr, inspection_bytes}, output.data(), inspection_bytes));
    CHECK(!upload_inspection_pixels({rgba.data(), 0}, output.data(), inspection_bytes));
    CHECK(!upload_inspection_pixels({rgba.data(), rgba.size()}, nullptr, inspection_bytes));
    CHECK(!upload_inspection_pixels({rgba.data(), rgba.size()}, output.data(), 0));
    CHECK(!upload_inspection_pixels({output.data(), inspection_bytes}, output.data(),
                                    inspection_bytes));
    CHECK(read_inspection_texture(nullptr, output.data(), inspection_bytes, api) ==
          E::invalid_target);
    CHECK(read_inspection_texture("", output.data(), inspection_bytes, api) == E::invalid_target);
    CHECK(read_inspection_texture("ignored", nullptr, inspection_bytes, api) == E::invalid_target);
    CHECK(read_inspection_texture("ignored", output.data(), 1, api) == E::invalid_target);
    input.resize(24);
    std::memcpy(input.data(), "S3TXv1\0\0", 8);
    put(8, 0x01000100);
    put(12, 1);
    put(16, inspection_bytes);
    put(20, inspection_crc32(rgba.data(), rgba.size()));
    input.insert(input.end(), rgba.begin(), rgba.end());
    const auto valid = input;
    const auto run = [&](E expected) {
        cursor = reads = closes = 0;
        io_error = false;
        CHECK(read_inspection_texture("ignored", output.data(), inspection_bytes, api) == expected);
        CHECK(closes == ((fault == "missing" || fault == "open") ? 0 : 1));
    };
    run(E::ok);
    CHECK(std::equal(rgba.begin(), rgba.end(), output.begin()));
    for (const auto *f : {"read1", "read2", "read3", "missing", "open", "close"}) {
        fault = f;
        run(fault == "missing" ? E::missing : fault == "close" ? E::close_failed : E::read_failed);
    }
    fault.clear();
    for (std::size_t offset = 0; offset < 24; ++offset) {
        input = valid;
        input[offset] ^= 1;
        run(offset < 20 ? E::invalid_data : E::verify_failed);
    }
    for (std::size_t length : {0U, 23U, 24U, 262167U}) {
        input.assign(valid.begin(), valid.begin() + length);
        run(E::invalid_data);
    }
    input = valid;
    input.push_back(0);
    run(E::invalid_data);
    input = valid;
    input.back() ^= 1;
    run(E::verify_failed);
    fault = "close"; // Preserve the original failure even if closing also fails.
    run(E::verify_failed);
}
