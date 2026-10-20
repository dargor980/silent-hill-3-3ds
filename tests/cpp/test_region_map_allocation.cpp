#include "sh3_observer/region_map.hpp"
#include "check.hpp"
#include <cstdlib>
#include <new>
namespace { bool forbidden{}; unsigned allocations{}; }
void* operator new(std::size_t n) {
  ++allocations;
  if (forbidden) throw std::bad_alloc{};
  if (auto p = std::malloc(n == 0 ? 1 : n)) return p;
  throw std::bad_alloc{};
}
void* operator new[](std::size_t n) { return ::operator new(n); }
void operator delete(void* p) noexcept { std::free(p); }
void operator delete[](void* p) noexcept { std::free(p); }
void operator delete(void* p, std::size_t) noexcept { std::free(p); }
void operator delete[](void* p, std::size_t) noexcept { std::free(p); }
using namespace sh3::observer;
struct Source final : RegionSource {
  unsigned queries{};
  RegionQuery query(std::uint64_t cursor, VmRegion& r) noexcept override {
    ++queries; forbidden = true;
    if (cursor != 0) return RegionQuery::end;
    r = {}; r.address = 4096; r.size = 4096; r.protection = r.maximum_protection = 1;
    return RegionQuery::found;
  }
};
int main() {
  Source s; RegionMap p;
  forbidden = true;
  auto failure = read_region_map(s,p);
  forbidden = false;
  CHECK(failure == RegionFailure::unavailable && s.queries == 0 && p.regions.empty() && p.bytes == 0);
  const auto before = allocations;
  auto success = read_region_map(s,p);
  forbidden = false;
  CHECK(success == RegionFailure::none && s.queries == 4 && p.regions.size() == 1 && p.bytes == 4096);
  CHECK(allocations == before+1);
}
