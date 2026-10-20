#pragma once
#include "sh3_observer/diagnostic_delivery.hpp"
#include "check.hpp"
#include <atomic>
#include <functional>
#include <thread>

namespace delivery_fixture {
using namespace sh3::observer;
using namespace std::chrono_literals;
using Clock = DiagnosticClock::Clock;
using Reason = DiagnosticRejection;
using Phase = DiagnosticWorkerPhase;
struct FakeClock final : DiagnosticClock {
  std::atomic<std::int64_t> ticks{10000000000LL};
  Clock::time_point now() noexcept override { return Clock::time_point(std::chrono::nanoseconds(ticks.load())); }
  void add(std::chrono::nanoseconds n) { ticks += n.count(); }
};
inline DiagnosticExpectation expectation() {
  DiagnosticExpectation e; e.profile=IdentityProfile::macos_platform_slices_v2;
  e.policy_evidence.fill(3);e.application_evidence.fill(4);e.platform_evidence.fill(5);return e;
}
inline DiagnosticRequest request(std::uint64_t sequence=1) {
  DiagnosticRequest r;r.challenge.fill(1);r.sequence=sequence;return r;
}
struct State {
  std::atomic<unsigned> samples{},closes{},creates{},prepares{};
  std::function<void(DiagnosticBudget&)> prepare_hook,sample_hook;
  std::function<void()> close_hook;
  bool close_ok{true};
};
struct Work final : DiagnosticWork {
  State& state;
  explicit Work(State& s):state(s){}
  Reason prepare(DiagnosticBudget& b) override {
    ++state.prepares;if(state.prepare_hook)state.prepare_hook(b);return Reason::none;
  }
  Reason sample(DiagnosticBudget& b,DiagnosticObservation& out) override {
    ++state.samples;if(state.sample_hook)state.sample_hook(b);
    out={};auto& r=out.inventory;auto e=expectation();
    r.profile=e.profile;r.scope=IdentityScope::application_headers;r.platform_assumed=true;
    r.process.pid=123;r.process.birth_ns=456;r.process.nonce.fill(2);
    r.file_objects.fill(6);r.classified_images.fill(7);r.policy_evidence=e.policy_evidence;
    r.application_evidence=e.application_evidence;r.platform_evidence=e.platform_evidence;
    r.loader_revision=3;r.application_images=26;r.platform_images=534;return Reason::none;
  }
  bool close() noexcept override {++state.closes;if(state.close_hook)state.close_hook();return state.close_ok;}
};
struct Factory final : DiagnosticWorkFactory {
  State& state;explicit Factory(State& s):state(s){}
  std::unique_ptr<DiagnosticWork> create(DiagnosticBudget&) override {++state.creates;return std::make_unique<Work>(state);}
};
inline std::unique_ptr<DiagnosticWorkFactory> factory(State& s){return std::make_unique<Factory>(s);}
template<class F>void eventually(F f) {
  auto limit=Clock::now()+3s;
  while(!f()){CHECK(Clock::now()<limit);std::this_thread::sleep_for(100us);}
}
inline DiagnosticCompletion take(DiagnosticWorker& w) {
  DiagnosticCompletion c;eventually([&]{CHECK(w.status().reason==Reason::none);return w.take_for_delivery(c);});return c;
}
inline void stopped(DiagnosticWorker& w,Reason reason,bool clean=true){
  CHECK(w.wait_stopped_until(Clock::now()+3s)==clean);auto s=w.status();
  CHECK(s.reason==reason && s.joined && s.cleanup_verified==clean && s.phase==Phase::stopped);
  CHECK(!w.delivery_checkpoint() && w.delivery_remaining()==0s && !w.complete_delivery());
}
} // namespace delivery_fixture
