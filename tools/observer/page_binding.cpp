#include "sh3_observer/page_binding.hpp"

namespace sh3::observer {
namespace {
bool valid_page(const PageReading& p) noexcept {
  return p.object != 0 && p.resident && p.external && !p.modified;
}
bool equal(const PageBindingResult& a, const PageBindingResult& b) noexcept {
  return same_file(a.file, b.file) && a.object == b.object && a.offset == b.offset;
}
}
PageBindingResult PageBinding::fail(PageFailure reason) noexcept {
  if (failure_ == PageFailure::none) failure_ = reason;
  baseline_ = {};
  PageBindingResult result{}; result.failure = failure_; return result;
}
void PageBinding::lose() noexcept { (void)fail(PageFailure::lost); }
PageBindingResult PageBinding::sample() noexcept {
  if (failure_ != PageFailure::none) return fail(failure_);
  if (address_ == 0) return fail(PageFailure::invalid);
  PageBindingResult result{};
  for (unsigned pass = 0; pass < 2; ++pass) {
    PageFileReading reference{}; PageReading target{};
    const bool available = pass == 0 ? (file_.read(reference) && pages_.read(address_, target))
                                    : (pages_.read(address_, target) && file_.read(reference));
    if (!available) return fail(PageFailure::unavailable);
    if (!valid_file(reference.file) || !valid_page(reference.page) || !valid_page(target) ||
        reference.page.offset != 0 || target.offset >= reference.file.size) return fail(PageFailure::invalid);
    if (reference.page.object != target.object) return fail(PageFailure::mismatch);
    const PageBindingResult now{reference.file, target.object, target.offset, PageFailure::none};
    if ((pass == 1 && !equal(result, now)) || (ready_ && !equal(baseline_, now))) return fail(PageFailure::changed);
    result = now;
  }
  baseline_ = result; ready_ = true; return result;
}
} // namespace sh3::observer
