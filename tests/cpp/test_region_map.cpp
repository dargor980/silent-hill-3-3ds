#include "sh3_observer/region_map.hpp"
#include "check.hpp"
#include <array>
#include <limits>
#include <string>
using namespace sh3::observer;
namespace {
VmRegion entry(std::uint64_t address = 4096) {
  VmRegion r{}; r.address = address; r.size = 4096; r.protection = 1; r.maximum_protection = 7; r.object = 123;
  return r;
}
struct Source final : RegionSource {
  std::vector<VmRegion> values{entry(), entry(16384)};
  unsigned calls{}, pass{};
  int fail_at{}, invalid_status_at{};
  bool remove{}, append{}, generate{};
  std::size_t generated_count{};
  int mutate{-1};
  RegionQuery query(std::uint64_t cursor, VmRegion& out) noexcept override {
    ++calls; if (cursor == 0) ++pass;
    if (calls == static_cast<unsigned>(fail_at)) return RegionQuery::unavailable;
    if (calls == static_cast<unsigned>(invalid_status_at)) return static_cast<RegionQuery>(99);
    const auto index = generate ? cursor/4096 : (cursor == 0 ? 0U : cursor <= 8192 ? 1U : 2U);
    const auto count = generate ? generated_count : values.size() + (pass == 2 && append ? 1 : 0) - (pass == 2 && remove ? 1 : 0);
    if (index >= count) return RegionQuery::end;
    out = generate ? entry(cursor) : index < values.size() ? values[index] : entry(32768);
    if (pass == 2 && mutate >= 0 && index == 0) {
      switch (mutate) {
        case 0: ++out.address; break; case 1: --out.size; break;
        case 2: ++out.offset; break; case 3: ++out.object; break;
        case 4: ++out.depth; break; case 5: out.protection = 3; break;
        case 6: out.maximum_protection = 5; break; case 7: ++out.inheritance; break;
        case 8: ++out.tag; break; case 9: ++out.flags; break;
        case 10: ++out.shadow_depth; break; case 11: ++out.share_mode; break;
        case 12: out.external = true; break; case 13: out.flags_available = true; break;
      }
    }
    return RegionQuery::found;
  }
};
void failure(Source& s, RegionFailure want) {
  RegionMap p{{entry()}, 4096};
  CHECK(read_region_map(s,p) == want && p.regions.empty() && p.bytes == 0);
}
void test(const std::string& name) {
  RegionMap p;
  if (name == "stable" || name == "empty" || name == "reserved") {
    Source s;
    if (name == "empty") s.values.clear();
    if (name == "reserved") { s.values[0].protection = 0; s.values[0].object = 0; }
    CHECK(read_region_map(s,p) == RegionFailure::none && p.regions.size() == s.values.size());
    CHECK(p.bytes == 4096*s.values.size() && s.calls == 2*(s.values.size()+1));
    for (std::size_t i = 0; i < s.values.size(); ++i) CHECK(same_region(s.values[i],p.regions[i]));
  } else if (name == "changed_fields") {
    for (int i = 0; i < 14; ++i) { Source s; s.mutate = i; failure(s,RegionFailure::changed); }
    auto a = entry(), b = a; CHECK(same_region(a,b)); b.submap = true; CHECK(!same_region(a,b));
  } else if (name == "changed_count") {
    Source s; s.remove = true; failure(s,RegionFailure::changed);
    Source t; t.append = true; failure(t,RegionFailure::changed);
  } else if (name == "unavailable") {
    for (int n = 1; n <= 6; ++n) {
      Source s; s.fail_at = n; failure(s,RegionFailure::unavailable);
      Source t; t.invalid_status_at = n; failure(t,RegionFailure::unavailable);
    }
  } else if (name == "invalid") {
    for (int n = 0; n < 7; ++n) {
      Source s; auto& r = s.values[0];
      if (n == 0) r.size = 0;
      if (n == 1) r.address = std::numeric_limits<std::uint64_t>::max()-1;
      if (n == 2) r.offset = std::numeric_limits<std::uint64_t>::max()-1;
      if (n == 3) r.protection = 16;
      if (n == 4) r.maximum_protection = 16;
      if (n == 5) r.maximum_protection = 0;
      if (n == 6) s.values[1].address = r.address;
      failure(s,RegionFailure::invalid);
    }
  } else if (name == "depth") {
    Source s; s.values[0].depth = region_depth_limit;
    CHECK(read_region_map(s,p) == RegionFailure::none);
    Source t; t.values[0].depth = region_depth_limit+1; failure(t,RegionFailure::capacity);
    Source u; u.values[0].submap = true; failure(u,RegionFailure::capacity);
  } else if (name == "capacity") {
    Source s; s.generate = true; s.generated_count = region_capacity;
    CHECK(read_region_map(s,p) == RegionFailure::none && p.regions.size() == region_capacity);
    CHECK(s.calls == 2*(region_capacity+1));
    Source t; t.generate = true; t.generated_count = region_capacity+1; failure(t,RegionFailure::capacity);
    CHECK(t.calls == region_capacity+1);
  } else if (name == "upper_bound") {
    Source s; s.values.resize(1); s.values[0].address = std::numeric_limits<std::uint64_t>::max()-4096;
    s.values[0].offset = s.values[0].address;
    CHECK(read_region_map(s,p) == RegionFailure::none && p.bytes == 4096);
  } else CHECK(false);
}
}
int main(int argc, char** argv) { CHECK(argc == 2); test(argv[1]); }
