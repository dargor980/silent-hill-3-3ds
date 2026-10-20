// Separate process: inject only this gate's allocation failure, without a test hook in production.
#include "check.hpp"
#include "sh3_observer/cooperative_gate.hpp"
#include <cstdlib>
#include <new>
namespace { bool fail_allocation=false; unsigned failures=0; }
void* operator new(std::size_t size) {
  if (fail_allocation) { ++failures; throw std::bad_alloc(); }
  if (void* p=std::malloc(size ? size : 1)) return p;
  throw std::bad_alloc();
}
void operator delete(void* pointer) noexcept { std::free(pointer); }
void operator delete(void* pointer,std::size_t) noexcept { std::free(pointer); }
int main() {
  using Gate=sh3::observer::CooperativeGate;
  Gate gate;
  auto existing=gate.enter(); CHECK(existing);
  fail_allocation=true;
  auto rejected=gate.enter();
  fail_allocation=false;
  CHECK(!rejected && failures==1);
  auto closure=gate.close(Gate::Clock::now()+std::chrono::seconds(5));
  CHECK(closure.poll()==Gate::State::draining);
  existing={}; CHECK(closure.poll()==Gate::State::held);
  closure.cancel(); CHECK(gate.enter());
}
