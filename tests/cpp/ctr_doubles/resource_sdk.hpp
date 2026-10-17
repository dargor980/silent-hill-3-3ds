#pragma once
#include <3ds.h>

namespace ctr_test {
struct ResourceSdk {
    bool homebrew{true};
    u32 heap{64}, linear{32}, linear_free{12}, vram_free{8}, region{128};
    s64 used{96};
    bool new_family{true};
    u32 cpu_percent{30};
    Result memory_result{0}, family_result{0}, cpu_result{0};
    unsigned samples{0};
    u64 ticks{0};
};
ResourceSdk &resource_sdk();
} // namespace ctr_test
