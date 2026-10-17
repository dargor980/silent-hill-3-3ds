// Own fixture for NASM object format, x86_64 ABI, linking and execution.
#include <array>
#include <cstdint>

extern "C" std::uint32_t synthetic_nasm_value(std::uint32_t value);

int main() {
    constexpr std::array<std::uint32_t, 4> inputs{0, 1, 17, 0xfffffff0u};
    for (const auto value : inputs) {
        if (synthetic_nasm_value(value) != ((value * 3u) ^ 0x5au)) return 1;
    }
    return 0;
}
