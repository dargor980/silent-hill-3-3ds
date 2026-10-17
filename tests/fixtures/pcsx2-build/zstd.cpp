// Own synthetic ABI/round-trip checks for the private host dependency build.
#include <zstd.h>

#include <algorithm>
#include <cstdint>
#include <iostream>
#include <vector>

int main() {
    if (ZSTD_versionNumber() != ZSTD_VERSION_NUMBER) return 1;
    for (const std::size_t size : {0u, 1u, 4096u, 65537u}) {
        for (const bool noisy : {false, true}) {
            std::vector<char> input(std::max(size, std::size_t{1}));
            std::uint32_t seed = 1;
            for (auto& byte : input) {
                seed = seed * 1664525u + 1013904223u;
                byte = noisy ? static_cast<char>(seed >> 24) : 'a';
            }
            std::vector<char> encoded(ZSTD_compressBound(size));
            const auto length = ZSTD_compress(encoded.data(), encoded.size(), input.data(), size, 3);
            if (ZSTD_isError(length)) return 2;
            std::vector<char> output(input.size());
            const auto decoded = ZSTD_decompress(output.data(), size, encoded.data(), length);
            if (decoded != size || !std::equal(input.begin(), input.begin() + size, output.begin())) return 3;
            if (!ZSTD_isError(ZSTD_decompress(output.data(), size, encoded.data(), length - 1))) return 4;
            if (size && !ZSTD_isError(ZSTD_decompress(output.data(), size - 1, encoded.data(), length))) return 5;
        }
    }
    std::cout << "Zstd: 8 round trips; truncation and output bounds passed\n";
}
