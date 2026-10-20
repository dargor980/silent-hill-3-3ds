// Own protocol probe. Exact provider fragments stay in a private include directory.
#include "check.hpp"
#include "sh3_observer/worker_control.hpp"
#include <atomic>
#include <cassert>
#include <cstdint>
#include <cstdio>
#include <limits>
#include <mutex>
#include <semaphore>
#include <string_view>
#include <thread>
#ifdef WB_NATIVE_SEMAPHORE
#include <mach/mach.h>
#include <mach/mach_error.h>
#include <mach/semaphore.h>
#include <mach/task.h>
#endif
using s32 = std::int32_t;
#define pxAssert(value) CHECK(value)
#define pxAssertMsg(value, message) CHECK(value)
namespace Threading {
#ifdef WB_NATIVE_SEMAPHORE
#include "kernel_class.inc"
#else
thread_local std::binary_semaphore* entering_wait = nullptr;
class KernelSemaphore {
  std::counting_semaphore<1024> semaphore_{0};
public:
  void Post() { semaphore_.release(); }
  void Wait() {
    if (entering_wait) { entering_wait->release(); entering_wait = nullptr; }
    semaphore_.acquire();
  }
};
#endif
#include "work_sema_class.inc"
}
#ifdef WB_NATIVE_SEMAPHORE
#include "kernel_darwin.inc"
#endif
#include "check_for_work.inc"
#include "wait_for_work.inc"
#include "wait_for_empty.inc"
#include "kill.inc"
#include "reset.inc"

using Control = sh3::observer::WorkerControl;
using Wakeup = sh3::observer::ControlWakeup;
using Token = Control::Token;
using Status = Control::Status;
using Stop = Control::StopResult;
using namespace std::chrono_literals;

template<class Predicate, class Wait> void until(Predicate ready, Wait wait) {
  const auto deadline = Wakeup::Clock::now() + 5s;
  while (!ready()) { CHECK(Wakeup::Clock::now() < deadline); wait(deadline); }
}
void online(Control& c, Wakeup& wake, std::uint32_t g = 1) {
  until([&] { auto s = c.lifecycle(); return s.online && s.generation == g; },
        [&](auto d) { wake.wait_until(d); });
}
void held(Control& c, Wakeup& wake, Token t = {1, 1}) {
  until([&] { return c.status(t) == Status::held; }, [&](auto d) { wake.wait_until(d); });
}
void request(Control& c, Threading::WorkSema& work, Token t = {1, 1}) {
  CHECK(c.request(t));
  work.NotifyOfWork(); // Proposed adapter: publish first; no data packet or producer hook.
}
bool park(Control& c, std::uint32_t generation = 1, std::unique_lock<std::mutex>* lock = nullptr) {
  const auto t = c.pending(generation);
  if (t == Token{}) return false;
  if (lock) lock->unlock();
  const bool accepted = c.acknowledge(t);
  if (accepted) {
    until([&] { return c.status(t) != Status::held; }, [&](auto d) { c.wait_worker_until(d); });
    CHECK(c.status(t) == Status::released);
  }
  if (lock) lock->lock();
  return accepted;
}
void finish(Control& c, Threading::WorkSema& work, std::uint32_t g = 1) {
  CHECK(c.stop(g) == Stop::stopped); work.Kill();
}

void before_wait() {
  Wakeup wake; Control c(wake); Threading::WorkSema work; std::binary_semaphore go(0);
  std::thread worker([&] {
    CHECK(c.start(1)); go.acquire(); work.WaitForWork(); CHECK(park(c)); finish(c, work);
  });
  online(c, wake); request(c, work); go.release(); held(c, wake);
  CHECK(c.release({1, 1})); worker.join();
}
#ifndef WB_NATIVE_SEMAPHORE
void sleeping_wait() {
  Wakeup wake; Control c(wake); Threading::WorkSema work; std::binary_semaphore sleeping(0);
  std::thread worker([&] {
    CHECK(c.start(1)); Threading::entering_wait = &sleeping;
    work.WaitForWork(); CHECK(park(c)); finish(c, work);
  });
  sleeping.acquire(); // WorkSema has already changed its state to SLEEPING.
  request(c, work); held(c, wake); CHECK(c.release({1, 1})); worker.join();
}
#endif
void cancelled_wake() {
  Wakeup wake; Control c(wake); Threading::WorkSema work; std::binary_semaphore go(0);
  std::thread worker([&] {
    CHECK(c.start(1)); go.acquire(); work.WaitForWork();
    CHECK(!park(c)); CHECK(!c.acknowledge({1, 1})); finish(c, work);
  });
  online(c, wake); request(c, work); CHECK(c.release({1, 1})); go.release(); worker.join();
  CHECK(c.status({1, 1}) == Status::offline);
}
void stop_held() {
  Wakeup wake; Control c(wake); Threading::WorkSema work; std::binary_semaphore checked(0);
  std::thread worker([&] {
    CHECK(c.start(1)); work.WaitForWork(); const auto t = c.pending(1);
    CHECK(c.acknowledge(t)); CHECK(c.stop(1) == Stop::retained); checked.release();
    until([&] { return c.status(t) != Status::held; }, [&](auto d) { c.wait_worker_until(d); });
    finish(c, work);
  });
  online(c, wake); request(c, work); checked.acquire(); CHECK(c.lifecycle().online);
  CHECK(c.release({1, 1})); worker.join(); CHECK(!c.lifecycle().online);
}
void idle_boundary() {
  Wakeup wake; Control c(wake); Threading::WorkSema work;
  std::binary_semaphore empty_checked(0), go(0); std::atomic<unsigned> idle_effects{0};
  std::thread worker([&] {
    CHECK(c.start(1)); CHECK(!work.CheckForWork()); empty_checked.release(); go.acquire();
    CHECK(park(c)); // Control is checked before the model's next idle effect.
    idle_effects.fetch_add(1); finish(c, work);
  });
  empty_checked.acquire(); request(c, work); go.release(); held(c, wake);
  CHECK(idle_effects.load() == 0); CHECK(c.release({1, 1})); worker.join();
  CHECK(idle_effects.load() == 1);
}
void busy_lock() {
  Wakeup wake; Control c(wake); Threading::WorkSema work; std::mutex busy;
  std::binary_semaphore acquired(0), go(0);
  std::thread worker([&] {
    std::unique_lock lock(busy); CHECK(c.start(1)); acquired.release(); go.acquire();
    CHECK(park(c, 1, &lock)); CHECK(lock.owns_lock()); finish(c, work);
  });
  acquired.acquire(); request(c, work); go.release(); held(c, wake);
  CHECK(busy.try_lock()); busy.unlock(); CHECK(c.release({1, 1})); worker.join();
}
void full_queue_dependency() {
  Wakeup wake; Control vu(wake), gs(wake); Threading::WorkSema vu_work, gs_work;
  std::binary_semaphore start_vu(0), start_gs(0), free_space(0), completion(0);
  std::atomic_bool full{true}; int vu_effect = 0, gs_effect = 0;
  // Synthetic queue/dependencies; these are not the provider's VU or GS loops.
  std::thread vu_worker([&] {
    CHECK(vu.start(1)); start_vu.acquire(); vu_work.WaitForWork();
    free_space.acquire(); CHECK(!full.load()); vu_effect = 17; completion.release();
    CHECK(park(vu)); finish(vu, vu_work);
  });
  std::thread gs_worker([&] {
    CHECK(gs.start(1)); start_gs.acquire(); gs_work.WaitForWork();
    CHECK(gs.pending(1) == Token{}); full.store(false); free_space.release();
    completion.acquire(); gs_effect = vu_effect + 1;
    // A later control kick must wake the same WorkSema after prior data work.
    until([&] { return gs.pending(1) != Token{}; }, [&](auto) { gs_work.WaitForWork(); });
    CHECK(park(gs)); finish(gs, gs_work);
  });
  online(vu, wake); online(gs, wake); CHECK(full.load());
  request(vu, vu_work); gs_work.NotifyOfWork(); start_vu.release(); start_gs.release();
  held(vu, wake); CHECK(vu_effect == 17); request(gs, gs_work); held(gs, wake);
  CHECK(gs_effect == 18 && !full.load());
  CHECK(gs.release({1, 1})); CHECK(vu.release({1, 1})); vu_worker.join(); gs_worker.join();
}
void restart() {
  Wakeup wake; Control c(wake); Threading::WorkSema work;
  std::binary_semaphore ended(0), restart_now(0);
  std::thread worker([&] {
    for (std::uint32_t g = 1; g <= 2; ++g) {
      work.Reset(); CHECK(c.start(g)); work.WaitForWork(); CHECK(park(c, g)); finish(c, work, g);
      if (g == 1) { ended.release(); restart_now.acquire(); }
    }
  });
  online(c, wake); request(c, work); held(c, wake); CHECK(c.release({1, 1})); ended.acquire();
  CHECK(c.status({1, 1}) == Status::offline); restart_now.release(); online(c, wake, 2);
  CHECK(!c.request({1, 2})); CHECK(!c.release({1, 1}));
  request(c, work, {2, 1}); held(c, wake, {2, 1}); CHECK(c.release({2, 1})); worker.join();
}
void close_pending() {
  Wakeup wake; Control c(wake); Threading::WorkSema work; std::binary_semaphore close_now(0);
  std::thread worker([&] {
    CHECK(c.start(1)); close_now.acquire(); work.WaitForWork(); finish(c, work);
    CHECK(!c.acknowledge({1, 1}));
  });
  online(c, wake); request(c, work); close_now.release(); worker.join();
  CHECK(c.status({1, 1}) == Status::offline); CHECK(!work.WaitForEmpty());
}
void timeout_pending() {
  Wakeup wake; Control c(wake); Threading::WorkSema work; std::binary_semaphore finish_work(0);
  std::thread worker([&] {
    CHECK(c.start(1)); finish_work.acquire(); work.WaitForWork(); CHECK(!park(c)); finish(c, work);
  });
  online(c, wake); request(c, work);
  const auto deadline = Wakeup::Clock::now() + 2ms;
  while (Wakeup::Clock::now() < deadline) wake.wait_until(deadline);
  CHECK(c.status({1, 1}) == Status::pending); CHECK(c.release({1, 1}));
  finish_work.release(); worker.join(); CHECK(c.status({1, 1}) == Status::offline);
}

int main(int argc, char** argv) {
  CHECK(argc == 2); const std::string_view name = argv[1];
  if (name == "before_wait") before_wait();
  else if (name == "cancelled_wake") cancelled_wake();
  else if (name == "stop_held") stop_held();
  else if (name == "idle_boundary") idle_boundary();
  else if (name == "busy_lock") busy_lock();
  else if (name == "full_queue_dependency") full_queue_dependency();
  else if (name == "restart") restart();
  else if (name == "close_pending") close_pending();
  else if (name == "timeout_pending") timeout_pending();
#ifndef WB_NATIVE_SEMAPHORE
  else if (name == "sleeping_wait") sleeping_wait();
#endif
  else CHECK(false);
  std::printf("{\"result\":\"PASS\",\"case\":\"%s\"}\n", argv[1]);
}
