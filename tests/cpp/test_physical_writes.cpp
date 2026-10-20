#include "check.hpp"
#include "sh3_observer/physical_writes.hpp"
#include "sh3_observer/capture.hpp"
#include <array>
#include <atomic>
#include <future>
#include <limits>
#include <string>
#include <thread>
#include <type_traits>
#include <utility>

using namespace sh3::observer;
constexpr std::uint64_t base = 1ULL << 40;
constexpr auto maximum = std::numeric_limits<std::uint64_t>::max();
LifetimePlan plan() { return {{{{1}}, 7, 100, 1000}, {0x1000, 0x2000, 0x3000, 0x4000}, 1000}; }
void valid() {
  LifetimeGuard g; CHECK(g.arm(plan())); PhysicalWrites p(g, base);
  CHECK(p.write(base - 4, 4, 1001)); CHECK(p.write(base + ram_size, 128, 1001));
  CHECK(g.report().accepted == 0);
  CHECK(p.write(base + 0x3020, 4, 1001)); CHECK(p.write(base + 0x302c, 4, 1001));
  CHECK(p.write(base, 4, 1002)); CHECK(p.write(base + ram_size - 1, 1, 1003));
  CHECK(g.report().writes == 4 && g.report().last.serial == 104);
  CHECK(g.report().last.session == plan().begin.session && g.report().last.epoch == 7);
}
void boundaries() {
  for (const auto anchor : {std::uint64_t{0}, base + 1, maximum - ram_size + 1}) {
    LifetimeGuard g; CHECK(g.arm(plan())); PhysicalWrites p(g, anchor);
    CHECK(!p.write(base, 4, 1001)); CHECK(g.report().reason == LifetimeReason::range);
  }
  for (const auto& [at,size] : std::array<std::pair<std::uint64_t,std::uint64_t>,6>{{
       {base,0},{maximum,1},{maximum-1,4},{base-1,2},{base+ram_size-1,2},{0,maximum}}}) {
    LifetimeGuard g; CHECK(g.arm(plan())); PhysicalWrites p(g, base);
    CHECK(!p.write(at,size,1001)); CHECK(g.report().reason == LifetimeReason::range);
  }
}
void protected_write() {
  // The same resolved destination covers any virtual alias; no address mask is used.
  for (const auto offset : {0x1000U,0x2000U,0x3000U,0x3010U,0x3024U,0x4000U}) {
    LifetimeGuard g; CHECK(g.arm(plan())); PhysicalWrites p(g,base);
    std::uint32_t destination = 42;
    { WriteBinding link(p); CHECK(link.connected());
      before_host_write(base+offset,4,1001);
      CHECK(destination == 42 && g.report().reason == LifetimeReason::protected_write);
      destination = 42; // A same-value store still happens after the rejection.
      before_host_write(base+offset,4,1002);
      destination = 9;
    }
    CHECK(destination == 9 && g.report().reason == LifetimeReason::protected_write);
  }
}
void unknown() {
  before_untracked_write(1001); // No binding: inert.
  LifetimeGuard g; CHECK(g.arm(plan())); PhysicalWrites p(g,base);
  { WriteBinding link(p); before_untracked_write(1001); }
  CHECK(g.report().reason == LifetimeReason::lost);
  CHECK(!p.write(base+0x3020,4,1002));
  CHECK(g.report().reason == LifetimeReason::lost);
}
void binding() {
  static_assert(!std::is_copy_constructible_v<WriteBinding>);
  static_assert(!std::is_move_constructible_v<WriteBinding>);
  static_assert(!std::is_copy_constructible_v<PhysicalWrites>);
  before_host_write(base,4,1001);
  LifetimeGuard a,b; CHECK(a.arm(plan())); CHECK(b.arm(plan()));
  PhysicalWrites pa(a,base),pb(b,base);
  { WriteBinding first(pa); CHECK(first.connected());
    { WriteBinding second(pb); CHECK(!second.connected()); before_host_write(base,4,1001); }
    before_host_write(base,4,1001);
  }
  before_host_write(base,4,1001);
  CHECK(a.report().writes == 2 && b.report().writes == 0);
  { WriteBinding next(pb); CHECK(next.connected()); before_host_write(base,4,1001); }
  CHECK(b.report().writes == 1);
}
void concurrent() {
  LifetimeGuard g; CHECK(g.arm(plan())); PhysicalWrites p(g,base);
  { WriteBinding link(p); CHECK(link.connected());
    std::array<std::thread,4> workers;
    for (auto& worker : workers) worker=std::thread([] {
      for (unsigned i=0;i<100;++i) before_host_write(base+0x3020,4,1001);
    });
    for (auto& worker : workers) worker.join();
  }
  CHECK(g.report().writes == 400 && g.report().last.serial == 500);
  CHECK(g.report().state == LifetimeState::armed);
  // Destroy the bridge/guard while a producer still invokes the global entry point.
  // The binding must disconnect before those objects die; later calls are inert.
  std::promise<void> started, released;
  auto first = started.get_future(); auto after = released.get_future();
  std::atomic<bool> disconnected{false}; std::thread producer;
  {
    LifetimeGuard owned; CHECK(owned.arm(plan())); PhysicalWrites bridge(owned,base);
    WriteBinding link(bridge); CHECK(link.connected());
    producer=std::thread([&] {
      before_host_write(base,4,1001); started.set_value();
      for (unsigned i=0;i<400 && !disconnected.load();++i) before_host_write(base,4,1001);
      after.wait();
      for (unsigned i=0;i<100;++i) before_host_write(base,4,1001);
    });
    first.wait();
  }
  disconnected=true; released.set_value(); producer.join();
}
void terminal() {
  LifetimeGuard idle; PhysicalWrites p(idle,base);
  CHECK(!p.write(base,4,1001)); CHECK(idle.report().reason == LifetimeReason::protocol);
  LifetimeGuard exhausted; auto limited=plan(); limited.limit=1; limited.begin.serial=maximum-1;
  CHECK(exhausted.arm(limited)); PhysicalWrites end(exhausted,base);
  CHECK(end.write(base,4,1001)); CHECK(!end.write(base,4,1001));
  CHECK(exhausted.report().reason == LifetimeReason::budget);
  LifetimeGuard backward; CHECK(backward.arm(plan())); PhysicalWrites reversed(backward,base);
  CHECK(!reversed.write(base,4,999)); CHECK(backward.report().reason == LifetimeReason::cycle);
}
int main(int argc,char** argv) {
  CHECK(argc == 2);
  const std::array<std::pair<const char*,void(*)()>,7> cases{{
    {"valid",valid},{"boundaries",boundaries},{"protected",protected_write},
    {"unknown",unknown},{"binding",binding},{"concurrent",concurrent},{"terminal",terminal}}};
  for (const auto& [name,run] : cases) if (name==std::string(argv[1])) {run(); return 0;}
  CHECK(false);
}
