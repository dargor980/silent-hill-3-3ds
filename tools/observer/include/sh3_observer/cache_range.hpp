#pragma once
#include "sh3_observer/artifact_manifest.hpp"
#include "sh3_observer/page_binding.hpp"

namespace sh3::observer {
struct CacheRange { std::uintptr_t address{}; std::uint64_t size{}, offset{}; };
inline constexpr std::size_t cache_range_capacity = 4096;
struct CacheRangeResult {
  FileDigest file{};
  std::uint64_t object{}, pages{}, bytes{};
  PageFailure failure{PageFailure::none};
};
// Covers precisely the supplied ranges; enumeration completeness is the caller's duty.
class CacheRangeGuard final {
public:
  CacheRangeGuard(FileDigest, std::vector<CacheRange>, std::uint64_t page_size,
                  PageFileSource&, PageSource&);
  CacheRangeGuard(const CacheRangeGuard&) = delete;
  CacheRangeGuard& operator=(const CacheRangeGuard&) = delete;
  CacheRangeResult sample() noexcept;
  void lose() noexcept;
private:
  CacheRangeResult fail(PageFailure) noexcept;
  bool reference(PageFileReading&) noexcept;
  const FileDigest expected_;
  const std::vector<CacheRange> ranges_;
  const std::uint64_t page_size_;
  PageFileSource& file_;
  PageSource& pages_;
  std::uint64_t baseline_object_{};
  PageFailure failure_{PageFailure::none};
};
} // namespace sh3::observer
