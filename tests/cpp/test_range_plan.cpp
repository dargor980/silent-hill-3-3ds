#include "sh3_observer/range_plan.hpp"
#include "check.hpp"
#include <algorithm>
#include <limits>
#include <random>
#include <set>
#include <string>
#include <tuple>

using namespace sh3::observer;
namespace {
RangeClaim claim(std::uint64_t id, std::uint64_t start, std::uint64_t size,
                 std::uint64_t initialized, std::uint32_t protection = 1) {
  return {{RangeDomain::image, id, 0}, start, size, initialized, protection};
}
void empty(const RangePlan& p) {
  CHECK(p.claims.empty() && p.atoms.empty() && p.dependencies.empty());
  CHECK(p.declared_bytes == 0 && p.reserved_bytes == 0 && p.unique_bytes == 0 && p.touched_pages == 0);
  CHECK(p.zero_fill_bytes == 0 && p.conflict_bytes == 0 && p.empty_claims == 0);
}
void rejects(const std::vector<RangeClaim>& claims, RangePlanFailure failure = RangePlanFailure::invalid,
             std::uint64_t page = 4096) {
  RangePlan out;
  CHECK(plan_ranges({claim(42, 100, 100, 100)}, 4096, out) == RangePlanFailure::none);
  CHECK(plan_ranges(claims, page, out) == failure);
  empty(out);
}
auto owner(const RangeOwner& o) { return std::make_tuple(o.domain, o.object, o.part); }
// Independent discrete-byte oracle: no event sorting or sweep state.
void oracle(const std::vector<RangeClaim>& input, const RangePlan& p, std::uint64_t page = 4096) {
  CHECK(p.claims.size() == input.size());
  std::uint64_t declared = 0, reserved = 0, unique = 0, zero = 0, conflicts = 0;
  std::size_t blanks = 0;
  std::set<std::uint64_t> pages;
  for (const auto& c : input) {
    declared += c.size;
    reserved += c.protection == 0 ? c.size : 0;
    blanks += c.size == 0;
    CHECK(std::count_if(p.claims.begin(), p.claims.end(), [&](const auto& q) {
      return owner(c.owner) == owner(q.owner) && c.address == q.address && c.size == q.size &&
             c.initialized_size == q.initialized_size && c.protection == q.protection;
    }) == 1);
  }
  for (std::size_t i = 1; i < p.claims.size(); ++i) CHECK(owner(p.claims[i-1].owner) < owner(p.claims[i].owner));
  std::size_t dependencies = 0;
  std::uint64_t end = 0;
  for (const auto& a : p.atoms) {
    CHECK(a.address >= end && a.size != 0 && a.dependency_count != 0);
    CHECK(a.first_dependency == dependencies);
    dependencies += a.dependency_count;
    CHECK(dependencies <= p.dependencies.size());
    end = a.address + a.size;
  }
  CHECK(dependencies == p.dependencies.size());
  std::set<std::uint64_t> bytes;
  for (const auto& c : input) if (c.protection != 0)
    for (auto x = c.address; x < c.address + c.size; ++x) bytes.insert(x);
  for (const auto& a : p.atoms) for (auto x = a.address; x < a.address + a.size; ++x) CHECK(bytes.count(x) == 1);
  for (const auto x : bytes) {
    std::vector<std::pair<std::size_t, RangeContent>> expected;
    std::set<std::uint32_t> protections;
    std::set<RangeContent> contents;
    for (std::size_t i = 0; i < p.claims.size(); ++i) {
      const auto& c = p.claims[i];
      if (c.protection == 0 || x < c.address || x >= c.address + c.size) continue;
      const auto content = x - c.address < c.initialized_size ? RangeContent::initialized : RangeContent::zero_fill;
      expected.push_back({i, content}); protections.insert(c.protection); contents.insert(content);
    }
    const bool conflict = protections.size() > 1 || contents.size() > 1;
    const RangeAtom* found = nullptr;
    for (const auto& a : p.atoms) if (a.address <= x && x < a.address + a.size) { CHECK(found == nullptr); found = &a; }
    CHECK(found && found->dependency_count == expected.size() && found->conflict == conflict);
    for (std::size_t i = 0; i < expected.size(); ++i) {
      const auto& d = p.dependencies[found->first_dependency + i];
      CHECK(d.claim == expected[i].first && d.content == expected[i].second);
    }
    ++unique; zero += contents.count(RangeContent::zero_fill); conflicts += conflict; pages.insert(x / page);
  }
  CHECK(p.declared_bytes == declared && p.reserved_bytes == reserved && p.empty_claims == blanks);
  CHECK(p.unique_bytes == unique && p.zero_fill_bytes == zero && p.conflict_bytes == conflicts && p.touched_pages == pages.size());
}
void test(const std::string& name) {
  RangePlan p;
  if (name == "empty") {
    CHECK(plan_ranges({}, 4096, p) == RangePlanFailure::none); empty(p);
  } else if (name == "aliases" || name == "nested" || name == "partial" || name == "zero_fill" || name == "conflict" || name == "reserved" || name == "pages") {
    std::vector<RangeClaim> in;
    if (name == "aliases") in = {claim(1, 100, 30, 30), claim(2, 100, 30, 30), claim(3, 100, 30, 30)};
    if (name == "nested") in = {claim(1, 100, 90, 90), claim(2, 110, 40, 40), claim(3, 120, 10, 10)};
    if (name == "partial") in = {claim(1, 100, 40, 40), claim(2, 120, 40, 40), claim(3, 170, 10, 10), claim(4, 180, 10, 10)};
    if (name == "zero_fill") in = {claim(1, 100, 40, 20), claim(2, 100, 40, 20), claim(3, 160, 10, 0)};
    if (name == "conflict") in = {claim(1, 100, 40, 40), claim(2, 110, 40, 0, 3), claim(3, 120, 40, 40, 5)};
    if (name == "reserved") in = {claim(1, 0, 100, 0, 0), claim(2, 0, 0, 0), claim(3, 30, 10, 10), claim(4, 200, 10, 0, 0)};
    if (name == "pages") in = {claim(1, 4094, 5, 2), claim(2, 4105, 4, 4), claim(3, 16383, 3, 3)};
    for (auto page : {4096, 16384}) { CHECK(plan_ranges(in, page, p) == RangePlanFailure::none); oracle(in, p, page); }
  } else if (name == "invalid") {
    for (int n = 0; n < 8; ++n) {
      auto c = claim(1, 100, 20, 20);
      if (n == 0) c.owner.object = 0;
      if (n == 1) c.owner.domain = static_cast<RangeDomain>(9);
      if (n == 2) c.protection = 8;
      if (n == 3) c.initialized_size = 21;
      if (n == 4) c.address = std::numeric_limits<std::uint64_t>::max() - 10;
      if (n == 5) c.address = 0;
      if (n == 6) c.size = 0;
      rejects({c}, RangePlanFailure::invalid, n == 7 ? 8192 : 4096);
    }
    rejects({claim(1, 0, std::numeric_limits<std::uint64_t>::max(), 0, 0), claim(2, 0, 1, 0, 0)});
  } else if (name == "owners") {
    auto a = claim(1, 100, 10, 10), b = a;
    rejects({a, b}); b.address = 200; rejects({a, b});
    b.owner.domain = RangeDomain::aot;
    auto c = a; c.owner.part = 1;
    CHECK(plan_ranges({a, b, c}, 4096, p) == RangePlanFailure::none); oracle({a, b, c}, p);
  } else if (name == "capacity") {
    std::vector<RangeClaim> in;
    for (std::size_t i = 0; i < range_claim_capacity; ++i) in.push_back(claim(i+1, 0, 0, 0));
    CHECK(plan_ranges(in, 4096, p) == RangePlanFailure::none && p.empty_claims == range_claim_capacity);
    in.push_back(claim(range_claim_capacity+1, 0, 0, 0)); rejects(in, RangePlanFailure::capacity);
  } else if (name == "dependencies") {
    std::vector<RangeClaim> in;
    for (std::size_t i = 0; i < 1024; ++i) in.push_back(claim(i+1, 100+i, 2048-2*i, 2048-2*i));
    CHECK(plan_ranges(in, 4096, p) == RangePlanFailure::none && p.dependencies.size() == range_dependency_capacity);
    in.push_back(claim(1025, 1124, 1, 1)); rejects(in, RangePlanFailure::capacity);
  } else if (name == "bytes") {
    auto c = claim(1, 100, range_unique_limit, range_unique_limit), d = c; d.owner.object = 2;
    CHECK(plan_ranges({c,d}, 4096, p) == RangePlanFailure::none);
    CHECK(p.unique_bytes == range_unique_limit && p.declared_bytes == 2*range_unique_limit);
    ++c.size; rejects({c}, RangePlanFailure::capacity);
    c = claim(1, std::numeric_limits<std::uint64_t>::max()-10, 10, 10);
    CHECK(plan_ranges({c}, 4096, p) == RangePlanFailure::none && p.unique_bytes == 10 && p.touched_pages == 1);
  } else if (name == "alias_input") {
    CHECK(plan_ranges({claim(1, 100, 30, 10)}, 4096, p) == RangePlanFailure::none);
    CHECK(plan_ranges(p.claims, 4096, p) == RangePlanFailure::none && p.unique_bytes == 30 && p.zero_fill_bytes == 20);
    CHECK(plan_ranges(p.claims, 1, p) == RangePlanFailure::invalid); empty(p);
  } else if (name == "oracle") {
    std::mt19937 rng(0x534833);
    for (unsigned trial = 0; trial < 400; ++trial) {
      std::vector<RangeClaim> in;
      for (unsigned i = 0, count = 1 + rng()%16; i < count; ++i) {
        auto size = rng()%40;
        in.push_back(claim(i+1, 4080+rng()%80, size, rng()%(size+1), rng()%8));
        if (i%3 == 0) in.back().owner.domain = RangeDomain::aot;
      }
      CHECK(plan_ranges(in, 4096, p) == RangePlanFailure::none); oracle(in, p);
      auto original = p;
      std::shuffle(in.begin(), in.end(), rng);
      CHECK(plan_ranges(in, 4096, p) == RangePlanFailure::none); oracle(in, p);
      CHECK(p.atoms.size() == original.atoms.size() && p.dependencies.size() == original.dependencies.size());
      for (std::size_t i = 0; i < p.atoms.size(); ++i) {
        auto a = p.atoms[i], b = original.atoms[i];
        CHECK(a.address == b.address && a.size == b.size && a.first_dependency == b.first_dependency && a.dependency_count == b.dependency_count && a.conflict == b.conflict);
      }
    }
  } else CHECK(false);
}
}
int main(int argc, char** argv) { CHECK(argc == 2); test(argv[1]); }
