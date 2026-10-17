#include "resource_sdk.hpp"
#include "check.hpp"

namespace ctr_test {
ResourceSdk &resource_sdk() {
    static ResourceSdk state;
    return state;
}
} // namespace ctr_test
bool envIsHomebrew() {
    ++ctr_test::resource_sdk().samples;
    return ctr_test::resource_sdk().homebrew;
}
u32 envGetHeapSize() { return ctr_test::resource_sdk().heap; }
u32 envGetLinearHeapSize() { return ctr_test::resource_sdk().linear; }
u32 linearSpaceFree() { return ctr_test::resource_sdk().linear_free; }
u32 vramSpaceFree() { return ctr_test::resource_sdk().vram_free; }
u32 osGetMemRegionSize(MemRegion region) {
    CHECK(region == MEMREGION_APPLICATION);
    return ctr_test::resource_sdk().region;
}
Result svcGetSystemInfo(s64 *out, u32 type, s32 param) {
    CHECK(out && type == 0 && param == MEMREGION_APPLICATION);
    const auto &s = ctr_test::resource_sdk();
    *out = s.used; // Write even on failure: caller must ignore this value.
    return s.memory_result;
}
Result APT_CheckNew3DS(bool *out) {
    CHECK(out);
    const auto &s = ctr_test::resource_sdk();
    *out = s.new_family;
    return s.family_result;
}
Result APT_GetAppCpuTimeLimit(u32 *out) {
    CHECK(out);
    const auto &s = ctr_test::resource_sdk();
    *out = s.cpu_percent;
    return s.cpu_result;
}
u64 svcGetSystemTick() { return ctr_test::resource_sdk().ticks += 10; }
