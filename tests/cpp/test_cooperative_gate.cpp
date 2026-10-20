#include "check.hpp"
#include "sh3_observer/cooperative_gate.hpp"
#include <condition_variable>
#include <functional>
#include <string>
#include <thread>
#include <type_traits>
#include <vector>
using Gate = sh3::observer::CooperativeGate;
using State = Gate::State;
auto later() { return Gate::Clock::now()+std::chrono::seconds(5); }
void open() {
  static_assert(!std::is_copy_constructible_v<Gate::Closure> && !std::is_move_constructible_v<Gate::Closure>);
  Gate gate; CHECK(gate.enter());
  { auto closure=gate.close(later()); CHECK(closure.poll()==State::held); CHECK(!gate.enter()); }
  CHECK(gate.enter());
}
void shared() {
  Gate gate; auto work=gate.enter(); auto copy=work;
  auto closure=gate.close(later()); work={}; CHECK(closure.poll()==State::draining);
  std::vector<std::function<void()>> queue;
  queue.emplace_back([copy]{ CHECK(copy); }); copy={};
  queue[0](); CHECK(closure.poll()==State::draining);
  auto retained=queue[0]; queue.clear(); CHECK(closure.poll()==State::draining);
  retained={}; CHECK(closure.poll()==State::held);
}
void draining() {
  Gate gate; auto first=gate.enter(); auto second=gate.enter();
  auto closure=gate.close(later()); CHECK(closure.poll()==State::draining); CHECK(!gate.enter());
  first={}; CHECK(closure.poll()==State::draining);
  second={}; CHECK(closure.poll()==State::held); CHECK(!gate.enter());
}
void contention() {
  Gate gate; auto owner=gate.close(later());
  { auto loser=gate.close(later()); CHECK(loser.poll()==State::rejected); loser.cancel(); CHECK(loser.poll()==State::rejected); }
  CHECK(owner.poll()==State::held); CHECK(!gate.enter()); owner.cancel(); CHECK(gate.enter());
}
void deadline() {
  Gate gate; auto work=gate.enter();
  auto closure=gate.close(Gate::Clock::now()); CHECK(closure.poll()==State::timed_out);
  work={}; CHECK(closure.poll()==State::timed_out); CHECK(!gate.enter());
  closure.cancel(); CHECK(gate.enter());
  const auto end=Gate::Clock::now()+std::chrono::milliseconds(10);
  auto empty=gate.close(end); // It may already expire if the process is descheduled.
  const auto state=empty.poll(); CHECK(state==State::held || state==State::timed_out);
  std::this_thread::sleep_until(end); CHECK(empty.poll()==State::timed_out); CHECK(!gate.enter());
}
void cancellation() {
  Gate gate; auto work=gate.enter();
  auto closure=gate.close(later()); closure.cancel(); closure.cancel();
  CHECK(closure.poll()==State::cancelled); CHECK(gate.enter());
  auto next=gate.close(later()); CHECK(next.poll()==State::draining);
  work={}; CHECK(next.poll()==State::held);
}
void capacity() {
  Gate zero(0); CHECK(!zero.enter()); auto empty=zero.close(later()); CHECK(empty.poll()==State::held);
  Gate one(1); auto work=one.enter(); auto copy=work; CHECK(!one.enter());
  work={}; CHECK(!one.enter()); copy={}; CHECK(one.enter());
}
void unwind() {
  Gate gate; bool caught=false;
  try { auto work=gate.enter(); CHECK(work); throw 1; } catch(int) { caught=true; }
  CHECK(caught);
  try { auto closure=gate.close(later()); CHECK(closure.poll()==State::held); throw 2; } catch(int) {}
  CHECK(gate.enter());
}
void concurrent() {
  Gate gate; std::mutex mutex; std::condition_variable cv; bool entered=false, release=false;
  int memory=0;
  std::thread worker([&]{
    auto work=gate.enter(); CHECK(work);
    { std::unique_lock<std::mutex> lock(mutex); entered=true; cv.notify_one(); cv.wait(lock,[&]{return release;}); }
    memory=42;
  });
  { std::unique_lock<std::mutex> lock(mutex); cv.wait(lock,[&]{return entered;}); }
  auto closure=gate.close(later()); CHECK(closure.poll()==State::draining);
  std::thread late([&]{ CHECK(!gate.enter()); }); late.join();
  { std::lock_guard<std::mutex> lock(mutex); release=true; } cv.notify_one();
  // Read only after the gate establishes publication, before joining the worker.
  State state; do { state=closure.poll(); std::this_thread::yield(); } while(state==State::draining);
  CHECK(state==State::held); CHECK(memory==42); worker.join();
}
int main(int argc,char** argv) {
  CHECK(argc==2); const std::string name=argv[1];
  if(name=="open")open(); else if(name=="shared")shared(); else if(name=="draining")draining();
  else if(name=="contention")contention(); else if(name=="deadline")deadline();
  else if(name=="cancellation")cancellation(); else if(name=="capacity")capacity();
  else if(name=="unwind")unwind(); else if(name=="concurrent")concurrent(); else CHECK(false);
}
