#include "check.hpp"
#include "sh3_observer/worker_control.hpp"
#include <cstdlib>
#include <new>

namespace { bool reject_allocation = false; }
void* operator new(std::size_t size) {
  if (reject_allocation) std::abort();
  if (void* p = std::malloc(size ? size : 1)) return p;
  throw std::bad_alloc();
}
void operator delete(void* p) noexcept { std::free(p); }
void operator delete(void* p, std::size_t) noexcept { std::free(p); }
int main() {
  using Control = sh3::observer::WorkerControl;
  using Wakeup = sh3::observer::ControlWakeup;
  Wakeup wake; Control control(wake);
  reject_allocation = true;
  CHECK(control.start(1));
  for (std::uint32_t id = 1; id <= 1000; ++id) {
    const Control::Token t{1, id};
    CHECK(control.request(t)); CHECK(control.pending(1) == t);
    CHECK(control.acknowledge(t)); CHECK(control.status(t) == Control::Status::held);
    CHECK(control.stop(1) == Control::StopResult::retained);
    CHECK(control.release(t)); CHECK(control.lifecycle().online);
    wake.try_wait(); control.wait_worker_until(Wakeup::Clock::now());
  }
  CHECK(control.stop(1) == Control::StopResult::stopped);
  reject_allocation = false;
}
