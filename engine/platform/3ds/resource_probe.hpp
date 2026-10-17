#pragma once

#include <cstdint>

namespace sh3::platform::ctr {
enum class ReadingStatus { available, unmeasured, sdk_error, invalid };
struct ResourceReading {
    ReadingStatus status{ReadingStatus::unmeasured};
    std::uint64_t value{0};
    std::int32_t result{0};
};
struct ResourceSnapshot {
    ResourceReading heap_capacity;
    ResourceReading linear_capacity;
    ResourceReading linear_free;
    ResourceReading vram_free;
    ResourceReading app_region_capacity;
    ResourceReading app_region_used;
    ResourceReading new_family;
    ResourceReading apt_cpu_limit_percent;
    ResourceReading app_budget;
    ResourceReading heap_free;
    ResourceReading cpu_clock_hz;
    bool homebrew{false};
};

class ResourceProbe final {
  public:
    [[nodiscard]] ResourceSnapshot sample() const noexcept;
};
// Decimal values preserve bytes/ticks exactly; UNKNOWN never formats as zero.
void format_reading(const ResourceReading &reading, char (&output)[21]) noexcept;
} // namespace sh3::platform::ctr
