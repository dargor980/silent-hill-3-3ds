#include "sh3_observer/range_plan.hpp"
#include "check.hpp"
#include <cstdlib>
#include <new>

namespace { long remaining = -1; }
void* operator new(std::size_t n) {
  if (remaining == 0) throw std::bad_alloc{};
  if (remaining > 0) --remaining;
  if (auto p = std::malloc(n == 0 ? 1 : n)) return p;
  throw std::bad_alloc{};
}
void* operator new[](std::size_t n) { return ::operator new(n); }
void operator delete(void* p) noexcept { std::free(p); }
void operator delete[](void* p) noexcept { std::free(p); }
void operator delete(void* p, std::size_t) noexcept { std::free(p); }
void operator delete[](void* p, std::size_t) noexcept { std::free(p); }
int main() {
  using namespace sh3::observer;
  std::vector<RangeClaim> in{{{RangeDomain::image, 1, 0}, 100, 40, 20, 1},
                             {{RangeDomain::aot, 1, 0}, 110, 50, 50, 1}};
  bool complete = false;
  for (long allocation = 0; allocation < 100; ++allocation) {
    RangePlan p;
    remaining = allocation;
    const auto result = plan_ranges(in, 4096, p);
    remaining = -1;
    if (result == RangePlanFailure::none) { CHECK(allocation > 5 && p.unique_bytes == 60); complete = true; break; }
    CHECK(result == RangePlanFailure::unavailable);
    CHECK(p.claims.empty() && p.atoms.empty() && p.dependencies.empty() && p.unique_bytes == 0 && p.declared_bytes == 0);
  }
  CHECK(complete);
}
