#include "check.hpp"
#include "resource_probe.hpp"
#include "resource_sdk.hpp"
#include <cstring>
#include <limits>

int main() {
    using namespace sh3::platform::ctr;
    auto &sdk = ctr_test::resource_sdk();
    ResourceProbe probe;
    auto sample = probe.sample();
    CHECK(sample.homebrew && sample.new_family.value == 1);
    CHECK(sample.heap_capacity.value == 64 && sample.linear_capacity.value == 32);
    CHECK(sample.linear_free.value == 12 && sample.vram_free.value == 8);
    CHECK(sample.app_region_capacity.value == 128 && sample.app_region_used.value == 96);
    CHECK(sample.app_region_used.status == ReadingStatus::available);
    CHECK(sample.apt_cpu_limit_percent.value == 30);
    CHECK(sample.app_budget.status == ReadingStatus::unmeasured);
    CHECK(sample.heap_free.status == ReadingStatus::unmeasured);
    CHECK(sample.cpu_clock_hz.status == ReadingStatus::unmeasured);
    char text[21]{};
    format_reading(sample.app_budget, text);
    CHECK(std::strcmp(text, "UNKNOWN") == 0);

    sdk.homebrew = sdk.new_family = false;
    sdk.linear_free = sdk.vram_free = sdk.cpu_percent = 0;
    sdk.used = 0;
    sample = probe.sample();
    CHECK(!sample.homebrew && sample.new_family.value == 0);
    CHECK(sample.linear_free.status == ReadingStatus::available && sample.linear_free.value == 0);
    CHECK(sample.vram_free.status == ReadingStatus::available && sample.vram_free.value == 0);
    CHECK(sample.app_region_used.status == ReadingStatus::available);
    CHECK(sample.apt_cpu_limit_percent.status == ReadingStatus::available);
    format_reading(sample.linear_free, text);
    CHECK(std::strcmp(text, "0") == 0);

    sdk.memory_result = -1;
    sdk.family_result = -2;
    sdk.cpu_result = -3;
    sdk.used = 96;
    sdk.new_family = true;
    sdk.cpu_percent = 100;
    sample = probe.sample();
    CHECK(sample.app_region_used.status == ReadingStatus::sdk_error);
    CHECK(sample.app_region_used.result == -1 && sample.app_region_used.value == 0);
    CHECK(sample.new_family.status == ReadingStatus::sdk_error && sample.new_family.result == -2);
    CHECK(sample.apt_cpu_limit_percent.status == ReadingStatus::sdk_error);
    CHECK(sample.apt_cpu_limit_percent.result == -3 && sample.apt_cpu_limit_percent.value == 0);
    format_reading(sample.app_region_used, text);
    CHECK(std::strcmp(text, "SDK_ERROR") == 0);

    sdk.memory_result = sdk.family_result = sdk.cpu_result = 0;
    sdk.used = -1;
    sdk.cpu_percent = 101;
    sdk.linear_free = 33;
    sample = probe.sample();
    CHECK(sample.app_region_used.status == ReadingStatus::invalid);
    CHECK(sample.apt_cpu_limit_percent.status == ReadingStatus::invalid);
    CHECK(sample.linear_free.status == ReadingStatus::invalid);
    format_reading(sample.linear_free, text);
    CHECK(std::strcmp(text, "INVALID") == 0);
    sdk.used = 129;
    CHECK(probe.sample().app_region_used.status == ReadingStatus::invalid);
    sdk.used = 128;
    sdk.cpu_percent = 100;
    sdk.linear_free = 32;
    sample = probe.sample();
    CHECK(sample.app_region_used.status == ReadingStatus::available);
    CHECK(sample.apt_cpu_limit_percent.status == ReadingStatus::available);
    CHECK(sample.linear_free.status == ReadingStatus::available);
    format_reading({ReadingStatus::available, std::numeric_limits<std::uint64_t>::max(), 0}, text);
    CHECK(std::strcmp(text, "18446744073709551615") == 0);
}
