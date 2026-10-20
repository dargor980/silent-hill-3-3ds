// Own orchestration; provider fragments are generated only in the private stage.
#include <atomic>
#include <cstdint>
#include <cstdlib>
#include <iostream>
#include <limits>
#include <semaphore>
#include <thread>

using s32 = std::int32_t;

static void require(bool value) {
    if (!value) std::abort();
}

#define pxAssert(value) require(value)
#define pxAssertMsg(value, message) require(value)
#define MTVU_LOG(...) ((void)0)

// Replace only the OS semaphore. Hooks order the adversaries without sleeps.
namespace Threading {
static std::binary_semaphore* wait_entered = nullptr;
class KernelSemaphore {
public:
    void Post() { semaphore_.release(); }
    void Wait() {
        if (wait_entered) wait_entered->release();
        semaphore_.acquire();
    }
private:
    std::counting_semaphore<1024> semaphore_{0};
};
#include "work_sema_class.inc"
} // namespace Threading

#include "check_for_work.inc"
#include "wait_for_work.inc"
#include "wait_for_empty.inc"
#include "kill.inc"
#include "reset.inc"

class VU_Thread {
public:
    Threading::WorkSema semaEvent;
    void WaitVU();
};
#include "wait_vu.inc"

static void completed_work_is_visible() {
    Threading::WorkSema sema;
    int effect = 0;
    std::atomic<bool> stop{false};
    sema.NotifyOfWork();
    std::thread worker([&] {
        sema.WaitForWork();
        effect = 42;
        sema.WaitForWork(); // Publishes empty, then sleeps until stop.
        require(stop.load());
        sema.Kill();
    });
    require(sema.WaitForEmpty());
    require(effect == 42);
    stop.store(true);
    sema.NotifyOfWork();
    worker.join();
}

static void dead_worker_is_not_success() {
    Threading::WorkSema sema;
    std::binary_semaphore waiting{0};
    Threading::wait_entered = &waiting;
    std::thread worker([&] {
        waiting.acquire();
        sema.Kill();
    });
    require(!sema.WaitForEmpty());
    worker.join();
    Threading::wait_entered = nullptr;
    require(!sema.WaitForEmpty()); // Also fails when already dead.
    sema.Reset();
    require(!sema.CheckForWork());
}

static void empty_can_overlap_idle_effects() {
    Threading::WorkSema sema;
    std::binary_semaphore waiting{0}, idle_entered{0}, finish_idle{0};
    std::atomic<bool> in_idle{false};
    Threading::wait_entered = &waiting;
    std::thread worker([&] {
        waiting.acquire();
        require(!sema.CheckForWork()); // MTGS idle path uses this signal.
        in_idle.store(true);
        idle_entered.release();
        finish_idle.acquire();
        in_idle.store(false);
        sema.Kill();
    });
    require(sema.WaitForEmpty());
    idle_entered.acquire();
    require(in_idle.load()); // A successful empty wait did not park the worker.
    finish_idle.release();
    worker.join();
    Threading::wait_entered = nullptr;
}

static void empty_does_not_close_producers() {
    Threading::WorkSema sema;
    std::binary_semaphore waiting{0}, consume_late{0};
    int effect = 0;
    Threading::wait_entered = &waiting;
    std::thread worker([&] {
        waiting.acquire();
        require(!sema.CheckForWork());
        consume_late.acquire();
        require(sema.CheckForWork());
        effect = 7;
        sema.Kill();
    });
    require(sema.WaitForEmpty());
    sema.NotifyOfWork(); // Still accepted after the successful empty wait.
    consume_late.release();
    worker.join();
    Threading::wait_entered = nullptr;
    require(effect == 7);
}

static void wait_vu_discards_failure() {
    VU_Thread vu;
    vu.semaEvent.Kill();
    require(!vu.semaEvent.WaitForEmpty());
    vu.WaitVU(); // Actual provider body returns normally, without a result.
}

int main() {
    completed_work_is_visible();
    dead_worker_is_not_success();
    empty_can_overlap_idle_effects();
    empty_does_not_close_producers();
    wait_vu_discards_failure();
    std::cout << "{\"result\":\"PASS\",\"cases\":5,"
                 "\"provider_work_sema_bodies\":true,"
                 "\"provider_wait_vu_body\":true,"
                 "\"os_semaphore_replaced\":true,"
                 "\"full_vm_executed\":false}\n";
}
