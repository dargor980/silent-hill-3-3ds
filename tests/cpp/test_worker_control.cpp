#include "check.hpp"
#include "sh3_observer/worker_control.hpp"
#include <barrier>
#include <limits>
#include <string_view>
#include <thread>
#include <type_traits>

using Control = sh3::observer::WorkerControl;
using Wakeup = sh3::observer::ControlWakeup;
using Status = Control::Status;
using Stop = Control::StopResult;
using Token = Control::Token;
using namespace std::chrono_literals;

// A wake is only a hint; even try_acquire_until may fail spuriously.
template<class Predicate, class Wait>
void until(Predicate predicate, Wait wait) {
  const auto deadline = Wakeup::Clock::now() + 5s;
  while (!predicate()) {
    CHECK(Wakeup::Clock::now() < deadline);
    wait(deadline);
  }
}
void consume(Wakeup& wake) {
  bool received = false;
  until([&] { return received; }, [&](auto deadline) { received = wake.wait_until(deadline); });
}

void defaults() {
  static_assert(!std::is_copy_constructible_v<Control> && !std::is_move_constructible_v<Control>);
  static_assert(!std::is_copy_constructible_v<Wakeup>);
  Wakeup wake; Control control(wake);
  CHECK(!control.lifecycle().online && control.lifecycle().generation == 0);
  CHECK(control.status({}) == Status::invalid);
  CHECK(control.status({1, 1}) == Status::invalid);
  CHECK(control.pending(0) == Token{});
  CHECK(!control.request({1, 1}));
  CHECK(!control.acknowledge({1, 1}));
  CHECK(!control.release({1, 1}));
  CHECK(!control.start(0));
  CHECK(control.stop(0) == Stop::stale);
  CHECK(control.stop(1) == Stop::stale);
}

void identity() {
  Wakeup wake; Control control(wake);
  CHECK(control.start(7)); CHECK(!control.start(8));
  CHECK(control.lifecycle().online && control.lifecycle().generation == 7);
  CHECK(control.status({7, 0}) == Status::invalid);
  CHECK(!control.request({0, 1})); CHECK(!control.request({7, 0}));
  CHECK(!control.request({6, 1})); CHECK(!control.request({8, 1}));
  const Token first{7, 3}, later{7, 5};
  CHECK(control.request(first));
  CHECK(control.status(first) == Status::pending);
  CHECK(control.pending(7) == first); CHECK(control.pending(8) == Token{});
  CHECK(!control.request(first)); CHECK(!control.request(later));
  CHECK(!control.acknowledge(later)); CHECK(!control.release(later));
  CHECK(!control.acknowledge({})); CHECK(!control.release({}));
  CHECK(control.acknowledge(first)); CHECK(!control.acknowledge(first));
  CHECK(control.pending(7) == Token{}); CHECK(control.status(first) == Status::held);
  CHECK(control.release(first)); CHECK(!control.release(first));
  CHECK(control.status(first) == Status::released);
  CHECK(!control.request(first)); CHECK(!control.request({7, 2}));
  CHECK(control.request(later)); CHECK(control.status(first) == Status::invalid);
  CHECK(!control.release(first)); CHECK(!control.acknowledge(first));
  CHECK(control.status(later) == Status::pending); CHECK(control.release(later));
}

void cancel() {
  Wakeup wake; Control control(wake); CHECK(control.start(1));
  const Token first{1, 1}, second{1, 2};
  CHECK(control.request(first)); CHECK(control.release(first));
  CHECK(!control.acknowledge(first)); CHECK(control.status(first) == Status::released);
  CHECK(control.request(second)); CHECK(!control.acknowledge(first));
  CHECK(control.acknowledge(second)); CHECK(!control.release(first));
  CHECK(control.status(second) == Status::held); CHECK(control.release(second));
  CHECK(!control.acknowledge(second)); CHECK(control.stop(1) == Stop::stopped);
  CHECK(control.status(second) == Status::offline); CHECK(!control.release(second));
}

void lifecycle() {
  Wakeup wake; Control control(wake); CHECK(control.start(5));
  const Token old{5, 1}; CHECK(control.request(old));
  CHECK(control.stop(4) == Stop::stale); CHECK(control.stop(5) == Stop::stopped);
  CHECK(control.status(old) == Status::offline); CHECK(!control.acknowledge(old));
  CHECK(control.stop(5) == Stop::stopped); CHECK(!control.lifecycle().online);
  CHECK(!control.start(5)); CHECK(!control.start(4)); CHECK(control.start(6));
  CHECK(control.status(old) == Status::invalid); CHECK(!control.release(old));
  CHECK(!control.request(old)); CHECK(!control.acknowledge(old));
  CHECK(control.stop(5) == Stop::stale); CHECK(control.request({6, 1}));
  CHECK(control.acknowledge({6, 1})); CHECK(control.release({6, 1}));
  CHECK(control.stop(6) == Stop::stopped);
}

void retained_stop() {
  Wakeup wake; Control control(wake); CHECK(control.start(1));
  const Token t{1, 1}; CHECK(control.request(t)); CHECK(control.acknowledge(t));
  for (unsigned i = 0; i < 100; ++i) {
    CHECK(control.stop(1) == Stop::retained); CHECK(control.lifecycle().online);
    CHECK(control.status(t) == Status::held); CHECK(!control.start(2));
  }
  CHECK(control.release(t)); CHECK(control.stop(1) == Stop::stopped);
  CHECK(control.start(2)); CHECK(control.status(t) == Status::invalid);
}

void exhaustion() {
  Wakeup wake; Control control(wake);
  constexpr auto generation = std::numeric_limits<std::uint32_t>::max();
  CHECK(control.start(generation));
  const Token last{generation, Control::max_request_id};
  CHECK(!control.request({generation, Control::max_request_id + 1}));
  CHECK(control.request(last)); CHECK(control.acknowledge(last)); CHECK(control.release(last));
  CHECK(!control.request(last)); CHECK(!control.request({generation, 1}));
  CHECK(!control.acknowledge({generation, Control::max_request_id + 1}));
  CHECK(!control.release({generation, Control::max_request_id + 1}));
  CHECK(control.stop(generation) == Stop::stopped);
  CHECK(!control.start(generation)); CHECK(!control.start(0)); CHECK(!control.start(1));
}

void wake_coalescing() {
  Wakeup wake; CHECK(!wake.try_wait());
  CHECK(!wake.wait_until(Wakeup::Clock::now()));
  for (unsigned i = 0; i < 1000; ++i) wake.notify();
  consume(wake); CHECK(!wake.try_wait());
  wake.notify(); consume(wake); CHECK(!wake.try_wait());
  // Exercise the nonblocking consumer without assuming its first try succeeds.
  wake.notify();
  const auto deadline = Wakeup::Clock::now() + 5s;
  while (!wake.try_wait()) CHECK(Wakeup::Clock::now() < deadline);
  CHECK(!wake.try_wait());
}

void wake_between_check_and_wait() {
  Wakeup wake;
  std::binary_semaphore checked(0), published(0);
  int payload = 0;
  std::thread producer([&] { checked.acquire(); payload = 47; wake.notify(); published.release(); });
  CHECK(!wake.try_wait()); checked.release(); published.acquire();
  // Notification is guaranteed to fall between the empty check and the wait.
  consume(wake); CHECK(payload == 47); producer.join();
}

void wake_publication() {
  Wakeup wake; std::binary_semaphore consumed(0);
  int payload = 0;
  std::thread producer([&] {
    for (int i = 1; i <= 2000; ++i) {
      payload = i; wake.notify(); consumed.acquire();
    }
  });
  for (int i = 1; i <= 2000; ++i) {
    // The wake, not another acquire primitive, publishes this plain payload.
    consume(wake); CHECK(payload == i); consumed.release();
  }
  producer.join();
}

void multiple_notifiers() {
  Wakeup wake; std::atomic<unsigned> completed{0};
  auto producer = [&] {
    for (unsigned i = 0; i < 1000; ++i) { completed.fetch_add(1); wake.notify(); }
  };
  std::thread first(producer), second(producer);
  until([&] { return completed.load() == 2000; }, [&](auto deadline) { wake.wait_until(deadline); });
  first.join(); second.join();
}

void coalesced_publication() {
  Wakeup wake; int payload = 0; std::atomic_bool published{false};
  wake.notify(); // The semaphore's original permit precedes the payload.
  std::thread producer([&] {
    payload = 59; wake.notify(); published.store(true, std::memory_order_relaxed);
  });
  // This relaxed flag schedules the test but does not publish the payload.
  until([&] { return published.load(std::memory_order_relaxed); }, [](auto) { std::this_thread::yield(); });
  consume(wake); CHECK(payload == 59); CHECK(!wake.try_wait()); producer.join();
}

void shared_owner() {
  Wakeup wake; Control vu(wake), gs(wake);
  CHECK(vu.start(1)); CHECK(gs.start(1)); consume(wake);
  CHECK(vu.request({1, 1})); CHECK(gs.request({1, 1}));
  CHECK(vu.acknowledge({1, 1})); consume(wake);
  CHECK(vu.status({1, 1}) == Status::held);
  CHECK(gs.status({1, 1}) == Status::pending); // A shared wake is not a GS ack.
  CHECK(gs.acknowledge({1, 1})); consume(wake);
  CHECK(gs.status({1, 1}) == Status::held);
  CHECK(gs.release({1, 1})); CHECK(vu.release({1, 1}));
}

void ack_publication() {
  Wakeup wake; Control control(wake); int payload = 0, request_payload = 0, release_payload = 0;
  std::thread worker([&] {
    CHECK(control.start(1));
    until([&] { return control.pending(1) != Token{}; }, [&](auto d) { control.wait_worker_until(d); });
    const auto t = control.pending(1); CHECK((t == Token{1, 1}));
    CHECK(request_payload == 31);
    payload = 83; CHECK(control.acknowledge(t));
    until([&] { return control.status(t) != Status::held; }, [&](auto d) { control.wait_worker_until(d); });
    CHECK(release_payload == 37);
    CHECK(control.stop(1) == Stop::stopped);
  });
  until([&] { return control.lifecycle().online; }, [&](auto d) { wake.wait_until(d); });
  const Token t{1, 1}; request_payload = 31; CHECK(control.request(t));
  // Polling the acquire predicate alone must publish the worker's prior write.
  until([&] { return control.status(t) == Status::held; }, [](auto) { std::this_thread::yield(); });
  CHECK(payload == 83); release_payload = 37; CHECK(control.release(t)); worker.join();
}

void release_ack_race() {
  Wakeup wake; Control control(wake); std::barrier rendezvous(2);
  std::thread worker([&] {
    CHECK(control.start(1)); rendezvous.arrive_and_wait();
    for (std::uint32_t i = 1; i <= 3000; ++i) {
      rendezvous.arrive_and_wait(); control.acknowledge({1, i}); rendezvous.arrive_and_wait();
    }
    CHECK(control.stop(1) == Stop::stopped);
  });
  rendezvous.arrive_and_wait();
  for (std::uint32_t i = 1; i <= 3000; ++i) {
    const Token t{1, i}; CHECK(control.request(t));
    rendezvous.arrive_and_wait(); CHECK(control.release(t)); rendezvous.arrive_and_wait();
    const auto status = control.status(t);
    CHECK(status == Status::released || (i == 3000 && status == Status::offline));
    CHECK(control.pending(1) == Token{});
  }
  worker.join();
}

void request_stop_race() {
  Wakeup wake; Control control(wake); std::barrier rendezvous(2);
  std::thread worker([&] {
    for (std::uint32_t g = 1; g <= 1500; ++g) {
      CHECK(control.start(g)); rendezvous.arrive_and_wait();
      const auto result = control.stop(g);
      CHECK(result == Stop::stopped || result == Stop::retry);
      rendezvous.arrive_and_wait();
      if (result == Stop::retry) CHECK(control.stop(g) == Stop::stopped);
      rendezvous.arrive_and_wait(); rendezvous.arrive_and_wait();
    }
  });
  for (std::uint32_t g = 1; g <= 1500; ++g) {
    rendezvous.arrive_and_wait(); const bool accepted = control.request({g, 1});
    rendezvous.arrive_and_wait(); rendezvous.arrive_and_wait();
    CHECK(!control.lifecycle().online);
    CHECK(control.status({g, 1}) == (accepted ? Status::offline : Status::invalid));
    rendezvous.arrive_and_wait();
  }
  worker.join();
}

void stop_release_race() {
  Wakeup wake; Control control(wake); std::barrier rendezvous(2);
  std::thread worker([&] {
    for (std::uint32_t g = 1; g <= 1500; ++g) {
      CHECK(control.start(g)); rendezvous.arrive_and_wait(); rendezvous.arrive_and_wait();
      CHECK(control.acknowledge({g, 1})); rendezvous.arrive_and_wait();
      const auto result = control.stop(g); CHECK(result == Stop::retained || result == Stop::stopped);
      rendezvous.arrive_and_wait();
      CHECK(control.stop(g) == Stop::stopped); rendezvous.arrive_and_wait(); rendezvous.arrive_and_wait();
    }
  });
  for (std::uint32_t g = 1; g <= 1500; ++g) {
    rendezvous.arrive_and_wait(); CHECK(control.request({g, 1})); rendezvous.arrive_and_wait();
    rendezvous.arrive_and_wait(); CHECK(control.release({g, 1})); rendezvous.arrive_and_wait();
    rendezvous.arrive_and_wait(); CHECK(control.status({g, 1}) == Status::offline);
    rendezvous.arrive_and_wait();
  }
  worker.join();
}

void full_data_queue() {
  Wakeup wake; Control control(wake);
  std::binary_semaphore checked_retention(0);
  // A synthetic one-slot queue: CPU has filled it before worker creation.
  // Its data path offers no space or wakeup to the control channel.
  std::atomic_bool full{true}; int queued = 91, applied = 0;
  std::thread worker([&] {
    CHECK(control.start(1));
    until([&] { return control.pending(1) != Token{}; }, [&](auto d) { control.wait_worker_until(d); });
    CHECK(full.load()); const auto t = control.pending(1);
    applied = queued; full.store(false); // Finish prior synthetic work before ack.
    CHECK(control.acknowledge(t));
    CHECK(control.stop(1) == Stop::retained);
    checked_retention.release();
    until([&] { return control.status(t) != Status::held; }, [&](auto d) { control.wait_worker_until(d); });
    CHECK(control.stop(1) == Stop::stopped);
  });
  until([&] { return control.lifecycle().online; }, [&](auto d) { wake.wait_until(d); });
  CHECK(full.load()); CHECK(control.request({1, 1}));
  until([&] { return control.status({1, 1}) == Status::held; }, [&](auto d) { wake.wait_until(d); });
  CHECK(!full.load() && applied == 91);
  checked_retention.acquire();
  CHECK(control.release({1, 1})); worker.join();
}

int main(int argc, char** argv) {
  CHECK(argc == 2); const std::string_view name = argv[1];
  if (name == "defaults") defaults();
  else if (name == "identity") identity();
  else if (name == "cancel") cancel();
  else if (name == "lifecycle") lifecycle();
  else if (name == "retained_stop") retained_stop();
  else if (name == "exhaustion") exhaustion();
  else if (name == "wake_coalescing") wake_coalescing();
  else if (name == "wake_between_check_and_wait") wake_between_check_and_wait();
  else if (name == "wake_publication") wake_publication();
  else if (name == "multiple_notifiers") multiple_notifiers();
  else if (name == "coalesced_publication") coalesced_publication();
  else if (name == "shared_owner") shared_owner();
  else if (name == "ack_publication") ack_publication();
  else if (name == "release_ack_race") release_ack_race();
  else if (name == "request_stop_race") request_stop_race();
  else if (name == "stop_release_race") stop_release_race();
  else if (name == "full_data_queue") full_data_queue();
  else CHECK(false);
}
