#include "check.hpp"
#include "sh3_observer/cpu_boundary.hpp"
#include <string>
#include <thread>
#include <type_traits>
using Cpu = sh3::observer::CpuBoundary;
void offline() {
  Cpu cpu; CHECK(!cpu.at_boundary());
  auto no=cpu.enter(); CHECK(!no.valid()); CHECK(!cpu.at_boundary());
}
void online() {
  static_assert(!std::is_copy_constructible_v<Cpu> && !std::is_move_constructible_v<Cpu>);
  static_assert(!std::is_copy_constructible_v<Cpu::Boundary> && !std::is_move_constructible_v<Cpu::Boundary>);
  static_assert(!std::is_copy_constructible_v<Cpu::Activity> && !std::is_move_constructible_v<Cpu::Activity>);
  Cpu cpu; cpu.set_online(true); CHECK(!cpu.at_boundary());
  { auto root=cpu.enter(); CHECK(root.valid()); CHECK(cpu.at_boundary()); }
  CHECK(!cpu.at_boundary()); auto next=cpu.enter(); CHECK(next.valid());
}
void activity() {
  Cpu cpu; cpu.set_online(true);
  { auto busy=cpu.activity(); auto rejected=cpu.enter(); CHECK(!rejected.valid()); CHECK(!cpu.at_boundary()); }
  auto root=cpu.enter(); CHECK(root.valid());
}
void revoked() {
  Cpu cpu; cpu.set_online(true);
  {
    auto root=cpu.enter(); CHECK(root.valid());
    { auto busy=cpu.activity(); CHECK(!root.valid()); CHECK(!cpu.at_boundary()); }
    CHECK(!root.valid()); CHECK(!cpu.at_boundary());
    auto retry=cpu.enter(); CHECK(!retry.valid());
  }
  auto next=cpu.enter(); CHECK(next.valid());
}
void nested_activity() {
  Cpu cpu; cpu.set_online(true);
  {
    auto outer=cpu.activity();
    { auto inner=cpu.activity(); auto no=cpu.enter(); CHECK(!no.valid()); }
    auto still_busy=cpu.enter(); CHECK(!still_busy.valid());
  }
  auto root=cpu.enter(); CHECK(root.valid());
}
void reentry() {
  Cpu cpu; cpu.set_online(true);
  {
    auto root=cpu.enter();
    { auto nested=cpu.enter(); CHECK(!nested.valid()); CHECK(!root.valid()); }
    auto retry=cpu.enter(); CHECK(!retry.valid()); CHECK(!cpu.at_boundary());
  }
  auto next=cpu.enter(); CHECK(next.valid());
}
void restart() {
  Cpu cpu; cpu.set_online(true);
  {
    auto root=cpu.enter(); cpu.set_online(false); CHECK(!root.valid());
    cpu.set_online(true); CHECK(!root.valid());
    auto retry=cpu.enter(); CHECK(!retry.valid());
  }
  { auto root=cpu.enter(); CHECK(root.valid()); cpu.set_online(true); CHECK(!root.valid()); }
  cpu.set_online(false); auto no=cpu.enter(); CHECK(!no.valid());
}
void unwind() {
  Cpu cpu; cpu.set_online(true);
  try { auto busy=cpu.activity(); throw 1; } catch (int) {}
  {
    auto root=cpu.enter(); CHECK(root.valid());
    try { auto busy=cpu.activity(); auto nested=cpu.activity(); throw 2; } catch (int) {}
    CHECK(!root.valid());
  }
  try { auto root=cpu.enter(); CHECK(root.valid()); throw 3; } catch (int) {}
  auto next=cpu.enter(); CHECK(next.valid());
}
thread_local Cpu per_thread;
void threads() {
  per_thread.set_online(true); auto root=per_thread.enter(); CHECK(root.valid());
  std::thread other([] { auto no=per_thread.enter(); CHECK(!no.valid());
    per_thread.set_online(true); auto own=per_thread.enter(); CHECK(own.valid()); });
  other.join(); CHECK(root.valid()); CHECK(per_thread.at_boundary());
}
int main(int argc, char** argv) {
  CHECK(argc==2); const std::string name=argv[1];
  if(name=="offline")offline(); else if(name=="online")online(); else if(name=="activity")activity();
  else if(name=="revoked")revoked(); else if(name=="nested_activity")nested_activity();
  else if(name=="reentry")reentry(); else if(name=="restart")restart();
  else if(name=="unwind")unwind(); else if(name=="threads")threads(); else CHECK(false);
}
