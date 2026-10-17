#include "resource_probe.hpp"
#include <3ds.h>
#include <cstdio>

namespace sh3::platform::ctr {
namespace {
ResourceReading value(std::uint64_t count) noexcept { return {ReadingStatus::available, count, 0}; }
ResourceReading checked(std::int32_t result, std::uint64_t count, bool valid) noexcept {
    if (R_FAILED(result)) {
        return {ReadingStatus::sdk_error, 0, result};
    }
    return {valid ? ReadingStatus::available : ReadingStatus::invalid, valid ? count : 0, result};
}
} // namespace

ResourceSnapshot ResourceProbe::sample() const noexcept {
    ResourceSnapshot snapshot;
    snapshot.homebrew = envIsHomebrew();
    snapshot.heap_capacity = value(envGetHeapSize());
    snapshot.linear_capacity = value(envGetLinearHeapSize());
    const auto linear_free = linearSpaceFree();
    snapshot.linear_free = checked(0, linear_free, linear_free <= snapshot.linear_capacity.value);
    snapshot.vram_free = value(vramSpaceFree());
    snapshot.app_region_capacity = value(osGetMemRegionSize(MEMREGION_APPLICATION));
    // osGetMemRegionUsed ignores the Result; read the same service explicitly.
    s64 used = 0;
    const auto memory_result = svcGetSystemInfo(&used, 0, MEMREGION_APPLICATION);
    snapshot.app_region_used = checked(memory_result, static_cast<std::uint64_t>(used),
                                       used >= 0 && static_cast<std::uint64_t>(used) <=
                                                        snapshot.app_region_capacity.value);
    bool is_new = false;
    const auto family_result = APT_CheckNew3DS(&is_new);
    snapshot.new_family = checked(family_result, is_new ? 1 : 0, true);
    u32 limit = 0;
    const auto cpu_result = APT_GetAppCpuTimeLimit(&limit);
    snapshot.apt_cpu_limit_percent = checked(cpu_result, limit, limit <= 100);
    return snapshot;
}

void format_reading(const ResourceReading &reading, char (&output)[21]) noexcept {
    switch (reading.status) {
    case ReadingStatus::available:
        std::snprintf(output, sizeof(output), "%llu",
                      static_cast<unsigned long long>(reading.value));
        break;
    case ReadingStatus::sdk_error:
        std::snprintf(output, sizeof(output), "SDK_ERROR");
        break;
    case ReadingStatus::invalid:
        std::snprintf(output, sizeof(output), "INVALID");
        break;
    case ReadingStatus::unmeasured:
        std::snprintf(output, sizeof(output), "UNKNOWN");
        break;
    }
}
} // namespace sh3::platform::ctr
