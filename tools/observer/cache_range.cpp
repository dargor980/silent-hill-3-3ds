#include "sh3_observer/cache_range.hpp"
#include <algorithm>
#include <limits>
#include <utility>

namespace sh3::observer {
namespace {
bool clean(const PageReading& p) noexcept {
  return p.object != 0 && p.resident && p.external && !p.modified;
}
}
CacheRangeGuard::CacheRangeGuard(FileDigest expected, std::vector<CacheRange> ranges,
    std::uint64_t page_size, PageFileSource& file, PageSource& pages)
  : expected_(expected), ranges_(std::move(ranges)), page_size_(page_size), file_(file), pages_(pages) {
  if (!valid_file(expected_.object) || expected_.object.size > cache_file_limit ||
      std::none_of(expected_.sha256.begin(), expected_.sha256.end(), [](auto b) { return b != 0; }) ||
      ranges_.empty() || ranges_.size() > cache_range_capacity || (page_size_ != 4096 && page_size_ != 16384)) {
    failure_ = PageFailure::invalid; return;
  }
  std::uint64_t previous_end{}, total{};
  for (const auto& range : ranges_) {
    if (range.address == 0 || range.size == 0 || range.address < previous_end ||
        range.size > std::numeric_limits<std::uintptr_t>::max() - range.address ||
        range.offset > expected_.object.size || range.size > expected_.object.size - range.offset ||
        range.size > cache_total_limit - total || range.address % page_size_ != range.offset % page_size_) {
      failure_ = PageFailure::invalid; return;
    }
    previous_end = range.address + range.size;
    total += range.size;
  }
}
CacheRangeResult CacheRangeGuard::fail(PageFailure reason) noexcept {
  if (failure_ == PageFailure::none) failure_ = reason;
  baseline_object_ = 0;
  CacheRangeResult result{}; result.failure = failure_; return result;
}
void CacheRangeGuard::lose() noexcept { (void)fail(PageFailure::lost); }
bool CacheRangeGuard::reference(PageFileReading& value) noexcept {
  if (!file_.read(value)) { (void)fail(PageFailure::unavailable); return false; }
  if (!clean(value.page) || value.page.offset != 0 || !valid_file(value.file)) {
    (void)fail(PageFailure::invalid); return false;
  }
  if (!same_file(value.file, expected_.object) ||
      (baseline_object_ != 0 && baseline_object_ != value.page.object)) {
    (void)fail(PageFailure::changed); return false;
  }
  return true;
}
CacheRangeResult CacheRangeGuard::sample() noexcept {
  if (failure_ != PageFailure::none) return fail(failure_);
  CacheRangeResult result{};
  for (unsigned pass = 0; pass < 2; ++pass) {
    PageFileReading before{}, after{};
    if (!reference(before)) return fail(failure_);
    if (pass == 1 && result.object != before.page.object) return fail(PageFailure::changed);
    result = {expected_, before.page.object, 0, 0, PageFailure::none};
    for (const auto& range : ranges_) {
      for (std::uint64_t delta = 0; delta < range.size;) {
        const auto address = range.address + delta;
        PageReading page{};
        if (!pages_.read(address, page)) return fail(PageFailure::unavailable);
        if (!clean(page)) return fail(PageFailure::invalid);
        if (page.object != before.page.object || page.offset != range.offset + delta) return fail(PageFailure::mismatch);
        ++result.pages;
        delta += std::min(page_size_ - address % page_size_, range.size - delta);
      }
      result.bytes += range.size;
    }
    if (!reference(after)) return fail(failure_);
    if (before.page.object != after.page.object) return fail(PageFailure::changed);
  }
  baseline_object_ = result.object;
  return result;
}
} // namespace sh3::observer
