// Project-owned compile probe; this is not a hardware execution test.
#include <3ds.h>
#include <array>
#include <type_traits>

static_assert(__cplusplus == 201703L, "The toolchain must compile as C++17");
static_assert(sizeof(u32) == 4, "The target must provide a 32-bit u32");

template <typename T> constexpr int integral_value(T value) {
    if constexpr (std::is_integral_v<T>) {
        return static_cast<int>(value);
    } else {
        return 0;
    }
}

int main() {
    const std::array values{20, 22};
    const auto [first, second] = values;
    return integral_value(first + second) == 42 ? 0 : 1;
}
