#include "check.hpp"
#include "sh3_observer/capture.hpp"
#include "sh3_observer/lifetime.hpp"
#include <array>
#include <functional>
#include <limits>
#include <string>
#include <type_traits>
#include <utility>
#include <vector>

using namespace sh3::observer;
constexpr auto maximum = std::numeric_limits<std::uint64_t>::max();
LifetimePlan plan() { return {{{{1}}, 7, 100, 1000}, {0x1000, 0x2000, 0x3000, 0x4000}, 256}; }
LifetimeNotice next(const LifetimeGuard& g, LifetimeKind kind = LifetimeKind::checkpoint,
                    std::uint32_t at = 0, std::uint32_t size = 0) {
  auto stamp = g.report().last;
  ++stamp.serial; ++stamp.cycle;
  return {stamp, kind, at, size};
}
void failed(const LifetimeGuard& g, LifetimeReason reason) {
  CHECK(g.report().state == LifetimeState::failed);
  CHECK(g.report().reason == reason);
}
void valid() {
  LifetimeGuard g;
  CHECK(g.report().state == LifetimeState::idle);
  CHECK(g.arm(plan()));
  CHECK(g.notify(next(g, LifetimeKind::write, 0, 1024)));
  CHECK(g.notify(next(g, LifetimeKind::write, plan().target.object + 32, 4)));
  CHECK(g.notify(next(g, LifetimeKind::write, plan().target.object + 44, 4)));
  CHECK(g.notify(next(g)));
  CHECK(g.notify(next(g, LifetimeKind::finish)));
  const auto r = g.report();
  CHECK(r.state == LifetimeState::sealed && r.reason == LifetimeReason::none);
  CHECK(r.accepted == 5 && r.writes == 3 && r.checkpoints == 1);
  CHECK(r.last.serial == 105 && r.last.cycle == 1005 && r.begin.cycle == 1000);
  CHECK(r.last.epoch == 7 && r.last.session == plan().begin.session);
}
void plans() {
  const std::vector<std::function<void(LifetimePlan&)>> mutations{
    [](auto& p) {p.begin.session = {};}, [](auto& p) {p.begin.epoch = 0;},
    [](auto& p) {p.begin.serial = 0;}, [](auto& p) {p.limit = 0;},
    [](auto& p) {p.limit = lifetime_max_notices + 1;},
    [](auto& p) {p.begin.serial = maximum;},
    [](auto& p) {p.target.root = ram_size;}, [](auto& p) {p.target.pool = ram_size - 20;},
    [](auto& p) {p.target.object = ram_size - 44;}, [](auto& p) {p.target.vtable = ram_size - 8;},
    [](auto& p) {p.target.root++;}, [](auto& p) {p.target.pool++;},
    [](auto& p) {p.target.object++;}, [](auto& p) {p.target.vtable++;},
    [](auto& p) {p.target.root = p.target.pool + 4;},
    [](auto& p) {p.target.vtable = p.target.object + 32;},
    [](auto& p) {p.target.pool = p.target.object - 20;},
    [](auto& p) {p.target.object = p.target.vtable;}
  };
  for (auto mutate : mutations) {
    auto p = plan(); mutate(p); LifetimeGuard g;
    CHECK(!g.arm(p)); failed(g, LifetimeReason::plan);
  }
  LifetimeGuard edge;
  auto p = plan(); p.limit = lifetime_max_notices;
  p.begin.serial = maximum - p.limit;
  p.target.root = 0; p.target.vtable = ram_size - 12;
  CHECK(edge.arm(p));
}
void identity() {
  for (unsigned i = 0; i < 16; ++i) {
    LifetimeGuard g; CHECK(g.arm(plan()));
    auto n = next(g); ++n.stamp.session[i];
    CHECK(!g.notify(n)); failed(g, LifetimeReason::identity);
  }
  for (const auto epoch : {0ULL, 6ULL, 8ULL}) {
    LifetimeGuard g; CHECK(g.arm(plan()));
    auto n = next(g); n.stamp.epoch = epoch;
    CHECK(!g.notify(n)); failed(g, LifetimeReason::epoch);
  }
}
void sequence() {
  for (const auto serial : {0ULL, 99ULL, 100ULL, 102ULL}) {
    LifetimeGuard g; CHECK(g.arm(plan()));
    auto n = next(g); n.stamp.serial = serial;
    CHECK(!g.notify(n)); failed(g, LifetimeReason::sequence);
    CHECK(g.report().last.serial == 100 && g.report().accepted == 0);
  }
  LifetimeGuard g; CHECK(g.arm(plan()));
  const auto duplicate = next(g); CHECK(g.notify(duplicate));
  CHECK(!g.notify(duplicate)); failed(g, LifetimeReason::sequence);
}
void cycles() {
  for (const auto cycle : {std::uint64_t{999}, 1001 + lifetime_max_cycles}) {
    LifetimeGuard g; CHECK(g.arm(plan()));
    auto n = next(g); n.stamp.cycle = cycle;
    CHECK(!g.notify(n)); failed(g, LifetimeReason::cycle);
  }
  LifetimeGuard paused; CHECK(paused.arm(plan()));
  auto n = next(paused); n.stamp.cycle = 1000;
  CHECK(paused.notify(n)); // Several host operations may share the paused CPU cycle.
  n = next(paused, LifetimeKind::finish); n.stamp.cycle = 1000;
  CHECK(!paused.notify(n)); failed(paused, LifetimeReason::cycle);
  LifetimeGuard edge; CHECK(edge.arm(plan()));
  n = next(edge, LifetimeKind::finish); n.stamp.cycle = 1000 + lifetime_max_cycles;
  CHECK(edge.notify(n));
  LifetimeGuard overflow;
  auto p = plan(); p.begin.cycle = maximum - 1;
  CHECK(overflow.arm(p)); CHECK(overflow.notify(next(overflow, LifetimeKind::finish)));
  LifetimeGuard wrapped; p.begin.cycle = maximum;
  CHECK(wrapped.arm(p));
  CHECK(!wrapped.notify(next(wrapped))); failed(wrapped, LifetimeReason::cycle);
}
void budget() {
  auto p = plan(); p.limit = 2; p.begin.serial = maximum - 2;
  LifetimeGuard g; CHECK(g.arm(p));
  CHECK(g.notify(next(g)));
  CHECK(g.notify(next(g, LifetimeKind::finish)));
  CHECK(g.report().last.serial == maximum && g.report().accepted == 2);
  LifetimeGuard exhausted; CHECK(exhausted.arm(p));
  CHECK(exhausted.notify(next(exhausted))); CHECK(exhausted.notify(next(exhausted)));
  CHECK(!exhausted.notify(next(exhausted, LifetimeKind::finish)));
  failed(exhausted, LifetimeReason::budget);
  CHECK(exhausted.report().last.serial == maximum && exhausted.report().accepted == 2);
}
void writes() {
  const auto t = plan().target;
  const std::array<std::pair<std::uint32_t, std::uint32_t>, 5> protected_ranges{
    {{t.root, 4}, {t.pool, 24}, {t.object, 32}, {t.object + 36, 8}, {t.vtable, 12}}};
  for (const auto& [at, size] : protected_ranges) {
    for (std::uint32_t byte = 0; byte < size; ++byte) {
      LifetimeGuard g; CHECK(g.arm(plan()));
      // Value is deliberately absent: even an unchanged store invalidates lifetime.
      CHECK(!g.notify(next(g, LifetimeKind::write, at + byte, 1)));
      failed(g, LifetimeReason::protected_write);
    }
  }
  for (const auto& [at, size] : std::array<std::pair<std::uint32_t, std::uint32_t>, 4>{
         {{t.object + 32, 5}, {t.object + 31, 2}, {t.object + 43, 2}, {0, ram_size}}}) {
    LifetimeGuard g; CHECK(g.arm(plan()));
    CHECK(!g.notify(next(g, LifetimeKind::write, at, size)));
    failed(g, LifetimeReason::protected_write);
  }
  // Release, reallocation and restored bytes cannot clear the first rejection.
  LifetimeGuard recycled; CHECK(recycled.arm(plan()));
  CHECK(!recycled.notify(next(recycled, LifetimeKind::write, t.object, 4)));
  CHECK(!recycled.notify(next(recycled, LifetimeKind::write, t.object + 16, 4)));
  CHECK(!recycled.notify(next(recycled, LifetimeKind::finish)));
  failed(recycled, LifetimeReason::protected_write);
}
void lifecycle() {
  const std::array<std::pair<LifetimeKind, LifetimeReason>, 7> cases{{
    {LifetimeKind::reset, LifetimeReason::reset}, {LifetimeKind::restore, LifetimeReason::restore},
    {LifetimeKind::remap, LifetimeReason::remap}, {LifetimeKind::settings, LifetimeReason::settings},
    {LifetimeKind::lost, LifetimeReason::lost}, {LifetimeKind::shutdown, LifetimeReason::shutdown},
    {LifetimeKind::cancel, LifetimeReason::cancelled}}};
  for (const auto& [kind, reason] : cases) {
    LifetimeGuard g; CHECK(g.arm(plan()));
    CHECK(!g.notify(next(g, kind))); failed(g, reason);
    // A failed load attempt or reset still invalidates; resuming cannot repair it.
    CHECK(!g.notify(next(g))); CHECK(!g.notify(next(g, LifetimeKind::finish)));
    failed(g, reason);
  }
}
void protocol() {
  LifetimeGuard idle;
  CHECK(!idle.notify({plan().begin, LifetimeKind::checkpoint}));
  failed(idle, LifetimeReason::protocol);
  LifetimeGuard rebound; CHECK(rebound.arm(plan()));
  CHECK(!rebound.arm(plan())); failed(rebound, LifetimeReason::protocol);
  for (const auto& [at, size] : std::array<std::pair<std::uint32_t, std::uint32_t>, 3>{
         {{1, 0}, {0, 1}, {1, 1}}}) {
    LifetimeGuard g; CHECK(g.arm(plan()));
    CHECK(!g.notify(next(g, LifetimeKind::finish, at, size)));
    failed(g, LifetimeReason::protocol);
  }
  LifetimeGuard unknown; CHECK(unknown.arm(plan()));
  CHECK(!unknown.notify(next(unknown, static_cast<LifetimeKind>(255))));
  failed(unknown, LifetimeReason::protocol);
}
void terminal() {
  static_assert(!std::is_copy_constructible_v<LifetimeGuard>);
  static_assert(!std::is_move_constructible_v<LifetimeGuard>);
  LifetimeGuard sealed; CHECK(sealed.arm(plan()));
  CHECK(sealed.notify(next(sealed, LifetimeKind::finish)));
  const auto before = sealed.report();
  CHECK(!sealed.arm(plan()));
  CHECK(!sealed.notify(next(sealed, LifetimeKind::write, plan().target.root, 4)));
  CHECK(!sealed.notify(next(sealed, LifetimeKind::restore)));
  const auto after = sealed.report();
  CHECK(after.state == before.state && after.reason == before.reason);
  CHECK(after.accepted == before.accepted && after.last.serial == before.last.serial);
  LifetimeGuard failed_guard; CHECK(failed_guard.arm(plan()));
  CHECK(!failed_guard.notify(next(failed_guard, LifetimeKind::lost)));
  CHECK(!failed_guard.arm(plan())); failed(failed_guard, LifetimeReason::lost);
}
void boundaries() {
  for (const auto& [at, size] : std::array<std::pair<std::uint32_t, std::uint32_t>, 5>{
         {{0, 0}, {ram_size, 1}, {ram_size - 1, 2}, {0xffffffffU, 4}, {0, ram_size + 1}}}) {
    LifetimeGuard g; CHECK(g.arm(plan()));
    CHECK(!g.notify(next(g, LifetimeKind::write, at, size))); failed(g, LifetimeReason::range);
  }
  LifetimeGuard end; CHECK(end.arm(plan()));
  CHECK(end.notify(next(end, LifetimeKind::write, ram_size - 1, 1)));
  // Byte-set oracle independent of interval arithmetic, including touching edges.
  const auto t = plan().target;
  for (const auto base : {t.root, t.pool, t.object, t.vtable}) {
    for (auto at = base - 16; at < base + 64; ++at) {
      for (unsigned size = 1; size <= 16; ++size) {
        bool protected_byte = false;
        for (auto b = at; b < at + size; ++b)
          protected_byte |= (b >= t.root && b < t.root + 4) ||
            (b >= t.pool && b < t.pool + 24) || (b >= t.vtable && b < t.vtable + 12) ||
            (b >= t.object && b < t.object + 48 &&
             !((b >= t.object + 32 && b < t.object + 36) || b >= t.object + 44));
        LifetimeGuard g; CHECK(g.arm(plan()));
        CHECK(g.notify(next(g, LifetimeKind::write, at, size)) == !protected_byte);
        if (protected_byte) failed(g, LifetimeReason::protected_write);
      }
    }
  }
}
int main(int argc, char** argv) {
  CHECK(argc == 2);
  const std::vector<std::pair<std::string, void(*)()>> scenarios{
    {"valid", valid}, {"plan", plans}, {"identity", identity}, {"sequence", sequence},
    {"cycles", cycles}, {"budget", budget}, {"writes", writes}, {"lifecycle", lifecycle},
    {"protocol", protocol}, {"terminal", terminal}, {"boundaries", boundaries}};
  for (const auto& [name, run] : scenarios) {
    if (name == argv[1]) { run(); return 0; }
  }
  CHECK(false);
}
