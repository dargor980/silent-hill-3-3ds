// Own C++20/x86_64 fixture. Does not link PCSX2 or load game data.
#include <array>
#include <bit>
#include <cstdint>
#include <cstdio>
#include <span>

#if !defined(__x86_64__)
#error "The reference PCSX2 build requires an x86_64 compiler target"
#endif

static_assert(sizeof(void*) == 8);
static_assert(std::endian::native == std::endian::little);
static_assert(std::bit_cast<std::uint32_t>(-13.5f) == 0xc1580000u);

int main() {
    constexpr std::array<std::uint32_t, 3> source{1, 3, 7};
    const std::span<const std::uint32_t> values{source};
    std::uint32_t sum = 0;
    for (const auto value : values) sum += value;
    if (sum != 11) return 1;
    std::puts("SH3 own fixture: C++20 x86_64 passed");
    return 0;
}
