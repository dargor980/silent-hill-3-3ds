// Own synthetic ABI/round-trip checks for the private host dependency build.
#include <lz4.h>

#include <algorithm>
#include <cstdint>
#include <iostream>
#include <vector>

int main() {
    if (LZ4_versionNumber() != LZ4_VERSION_NUMBER) return 1;
    for (const int size : {0, 1, 4096, 65537}) {
        for (const bool noisy : {false, true}) {
            std::vector<char> input(std::max(size, 1));
            std::uint32_t seed = 1;
            for (auto& byte : input) {
                seed = seed * 1664525u + 1013904223u;
                byte = noisy ? static_cast<char>(seed >> 24) : 'a';
            }
            std::vector<char> encoded(LZ4_compressBound(size));
            const int length = LZ4_compress_default(input.data(), encoded.data(), size, static_cast<int>(encoded.size()));
            if (length <= 0) return 2;
            std::vector<char> output(input.size());
            const int decoded = LZ4_decompress_safe(encoded.data(), output.data(), length, size);
            if (decoded != size || !std::equal(input.begin(), input.begin() + size, output.begin())) return 3;
            if (size && LZ4_decompress_safe(encoded.data(), output.data(), length, size - 1) >= 0) return 4;
            if (LZ4_compress_default(input.data(), encoded.data(), size, 0) != 0) return 5;
        }
    }
    std::cout << "LZ4: 8 round trips and output bounds passed\n";
}
