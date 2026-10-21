#include "check.hpp"
#include "sh3/platform/inspection_crc32.hpp"
#include "sh3/platform/inspection_geometry.hpp"
#include <algorithm>
#include <array>
#include <cerrno>
#include <cstring>
#include <limits>
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
void put(std::size_t offset, std::uint32_t value) {
    for (unsigned i = 0; i < 4; ++i)
        input[offset + i] = value >> (i * 8);
}
} // namespace

int main(int argc, char **argv) {
    using V = sh3::domain::SceneVertex;
    std::vector<V> output(inspection_max_vertices + 2);
    output.front().u = output.back().u = 123.F;
    std::size_t count = 999;
    const std::array<V, 3> triangle{{
        {{-1, -1, -2}, 0, 0, {1, 0, 0}},
        {{1, -1, -2}, 1, 0, {0, 1, 0}},
        {{0, 1, -2}, 0, 1, {0, 0, 1}},
    }};
    if (argc == 2) {
        const auto result = read_inspection_geometry(argv[1], output.data(), 3072, count);
        if (result != E::ok)
            return 2;
        CHECK(count == 3);
        CHECK(std::memcmp(output.data(), triangle.data(), sizeof(triangle)) == 0);
        return 0;
    }
    CHECK(valid_inspection_mesh({triangle.data(), 3}));
    CHECK(!valid_inspection_mesh({nullptr, 3}));
    for (std::size_t n : {0U, 1U, 2U, 4U, 3073U})
        CHECK(!valid_inspection_mesh({triangle.data(), n}));
    std::vector<V> maximum;
    for (unsigned i = 0; i < 1024; ++i)
        maximum.insert(maximum.end(), triangle.begin(), triangle.end());
    CHECK(valid_inspection_mesh({maximum.data(), maximum.size()}));
    input.resize(24);
    std::memcpy(input.data(), "S3GMv1\0\0", 8);
    put(8, 3);
    put(12, 32);
    put(16, 96);
    // Independent little-endian fixture, not a native struct dump.
    for (const auto &vertex : triangle) {
        for (const auto value : {vertex.position.x, vertex.position.y, vertex.position.z, vertex.u,
                                 vertex.v, vertex.color.x, vertex.color.y, vertex.color.z}) {
            std::uint32_t bits{};
            std::memcpy(&bits, &value, 4);
            const auto offset = input.size();
            input.resize(offset + 4);
            put(offset, bits);
        }
    }
    put(20, inspection_crc32(input.data() + 24, 96));
    const auto valid = input;
    const auto run = [&](E expected, std::size_t capacity = 3072) {
        cursor = reads = closes = 0;
        io_error = false;
        count = 999;
        CHECK(read_inspection_geometry("ignored", output.data() + 1, capacity, count, api) ==
              expected);
        CHECK(count == (expected == E::ok ? 3U : 0U));
        CHECK(closes == ((fault == "missing" || fault == "open") ? 0 : 1));
        CHECK(output.front().u == 123.F && output.back().u == 123.F);
    };
    run(E::ok);
    CHECK(std::memcmp(output.data() + 1, triangle.data(), sizeof(triangle)) == 0);
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
    for (std::size_t length : {0U, 23U, 24U, 119U}) {
        input.assign(valid.begin(), valid.begin() + length);
        run(E::invalid_data);
    }
    input = valid;
    input.push_back(0);
    run(E::invalid_data);
    input = valid;
    input.back() ^= 1;
    run(E::verify_failed);
    fault = "close";
    run(E::verify_failed);
    fault.clear();
    for (std::size_t component = 0; component < 8; ++component) {
        for (const float bad : {std::numeric_limits<float>::quiet_NaN(),
                                std::numeric_limits<float>::infinity(), -5.F, 5.F}) {
            input = valid;
            std::uint32_t bits{};
            std::memcpy(&bits, &bad, 4);
            put(24 + component * 4, bits);
            put(20, inspection_crc32(input.data() + 24, 96));
            run(E::invalid_data);
        }
    }
    for (std::size_t component = 5; component < 8; ++component) {
        input = valid;
        put(24 + component * 4, 0xBF000000); // -0.5, color only.
        put(20, inspection_crc32(input.data() + 24, 96));
        run(E::invalid_data);
    }
    input = valid;
    std::copy_n(input.begin() + 24, 32, input.begin() + 56);
    put(20, inspection_crc32(input.data() + 24, 96));
    run(E::invalid_data);
    input = valid;
    put(8, 6);
    put(16, 192);
    run(E::invalid_data, 3); // Header is valid in format but caller capacity is too small.
    for (const auto *path : {static_cast<const char *>(nullptr), ""}) {
        count = 9;
        CHECK(read_inspection_geometry(path, output.data(), 3, count, api) == E::invalid_target);
        CHECK(count == 0);
    }
    CHECK(read_inspection_geometry("ignored", nullptr, 3, count, api) == E::invalid_target);
    for (std::size_t capacity : {0U, 2U, 3073U})
        CHECK(read_inspection_geometry("ignored", output.data(), capacity, count, api) ==
              E::invalid_target);
}
