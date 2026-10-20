#include "sh3_observer/range_plan.hpp"
#include <algorithm>
#include <limits>
#include <new>
#include <set>
#include <tuple>
#include <utility>

namespace sh3::observer {
namespace {
auto key(const RangeOwner& o) noexcept { return std::make_tuple(o.domain, o.object, o.part); }
struct Event { std::uint64_t address; std::size_t claim; bool start; };
RangePlanFailure build(const std::vector<RangeClaim>& input, std::uint64_t page_size, RangePlan& p) {
  if (page_size != 4096 && page_size != 16384) return RangePlanFailure::invalid;
  if (input.size() > range_claim_capacity) return RangePlanFailure::capacity;
  p.claims = input;
  std::sort(p.claims.begin(), p.claims.end(), [](const auto& a, const auto& b) { return key(a.owner) < key(b.owner); });
  std::vector<Event> events;
  events.reserve(3 * input.size());
  const auto maximum = std::numeric_limits<std::uint64_t>::max();
  for (std::size_t i = 0; i < p.claims.size(); ++i) {
    const auto& c = p.claims[i];
    if ((c.owner.domain != RangeDomain::image && c.owner.domain != RangeDomain::aot) ||
        c.owner.object == 0 || (i != 0 && key(c.owner) == key(p.claims[i - 1].owner)) ||
        c.protection > 7 || c.initialized_size > c.size || c.size > maximum - c.address ||
        c.size > maximum - p.declared_bytes || (c.size != 0 && c.protection != 0 && c.address == 0))
      return RangePlanFailure::invalid;
    p.declared_bytes += c.size;
    if (c.size == 0) { ++p.empty_claims; continue; }
    if (c.protection == 0) { p.reserved_bytes += c.size; continue; }
    events.push_back({c.address, i, true});
    // A boundary event also splits the atom; membership remains unchanged.
    if (c.initialized_size != 0 && c.initialized_size < c.size)
      events.push_back({c.address + c.initialized_size, i, true});
    events.push_back({c.address + c.size, i, false});
  }
  std::sort(events.begin(), events.end(), [](const auto& a, const auto& b) { return a.address < b.address; });
  std::set<std::size_t> active;
  std::uint64_t last_page{};
  bool have_page = false;
  for (std::size_t i = 0; i < events.size();) {
    const auto start = events[i].address;
    do {
      const auto& e = events[i];
      if (e.start) active.insert(e.claim); else active.erase(e.claim);
      ++i;
    } while (i < events.size() && events[i].address == start);
    if (i == events.size() || active.empty()) continue;
    const auto size = events[i].address - start;
    if (size > range_unique_limit - p.unique_bytes || p.atoms.size() == range_atom_capacity ||
        active.size() > range_dependency_capacity - p.dependencies.size()) return RangePlanFailure::capacity;
    RangeAtom atom{start, size, p.dependencies.size(), active.size(), false};
    const auto& first = p.claims[*active.begin()];
    const bool first_zero = start - first.address >= first.initialized_size;
    bool any_zero = false;
    for (const auto index : active) {
      const auto& c = p.claims[index];
      const bool zero = start - c.address >= c.initialized_size;
      atom.conflict |= zero != first_zero || c.protection != first.protection;
      any_zero |= zero;
      p.dependencies.push_back({index, zero ? RangeContent::zero_fill : RangeContent::initialized});
    }
    p.atoms.push_back(atom);
    p.unique_bytes += size;
    if (any_zero) p.zero_fill_bytes += size;
    if (atom.conflict) p.conflict_bytes += size;
    const auto begin_page = start / page_size, end_page = (start + size - 1) / page_size;
    const auto new_page = have_page ? std::max(begin_page, last_page + 1) : begin_page;
    if (new_page <= end_page) p.touched_pages += end_page - new_page + 1;
    last_page = end_page;
    have_page = true;
  }
  return RangePlanFailure::none;
}
}
RangePlanFailure plan_ranges(const std::vector<RangeClaim>& input, std::uint64_t page_size,
                             RangePlan& output) noexcept {
  try {
    RangePlan result;
    const auto failure = build(input, page_size, result);
    output = failure == RangePlanFailure::none ? std::move(result) : RangePlan{};
    return failure;
  } catch (const std::bad_alloc&) {
    output = {};
    return RangePlanFailure::unavailable;
  }
}
} // namespace sh3::observer
