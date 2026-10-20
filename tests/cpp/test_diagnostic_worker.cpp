#include "sh3_observer/diagnostic_worker.hpp"
#include "check.hpp"
#include <algorithm>
#include <atomic>
#include <condition_variable>
#include <functional>
#include <mutex>
#include <stdexcept>
#include <string>
#include <thread>

using namespace sh3::observer;
using namespace std::chrono_literals;
namespace {
using Clock = DiagnosticClock::Clock;
using Reason = DiagnosticRejection;
using Phase = DiagnosticWorkerPhase;
struct FakeClock final : DiagnosticClock {
  std::atomic<std::int64_t> ticks{10000000000LL};
  Clock::time_point now() noexcept override { return Clock::time_point(std::chrono::nanoseconds(ticks.load())); }
  void add(std::chrono::nanoseconds value) { ticks += value.count(); }
};
struct Fixture {
  DiagnosticExpectation expectation;
  DiagnosticRequest request;
  DiagnosticObservation observation;
  Fixture() {
    expectation.profile = IdentityProfile::macos_platform_slices_v2;
    expectation.policy_evidence.fill(3); expectation.application_evidence.fill(4);
    expectation.platform_evidence.fill(5);
    request.challenge.fill(1); request.sequence = 1;
    auto& r = observation.inventory;
    r.profile = expectation.profile; r.scope = IdentityScope::application_headers; r.platform_assumed = true;
    r.process.pid = 123; r.process.birth_ns = 123456; r.process.nonce.fill(2);
    r.file_objects.fill(6); r.classified_images.fill(7); r.policy_evidence = expectation.policy_evidence;
    r.application_evidence = expectation.application_evidence; r.platform_evidence = expectation.platform_evidence;
    r.loader_revision = 3; r.application_images = 26; r.platform_images = 534;
  }
};
struct Control {
  std::function<void(const std::string&, DiagnosticBudget&)> hook;
  std::function<void(DiagnosticObservation&)> mutate;
  std::atomic<int> creates{}, prepares{}, samples{}, closes{}, destroys{}, factory_destroys{};
  Reason prepare_reason{Reason::none}, sample_reason{Reason::none};
  bool null_work{}, close_ok{true};
  std::thread::id worker, destroy_thread, factory_thread;
};
struct Work final : DiagnosticWork {
  Control& c; DiagnosticObservation observation;
  Work(Control& control, DiagnosticObservation value) : c(control), observation(value) {}
  ~Work() override { c.destroy_thread = std::this_thread::get_id(); ++c.destroys; }
  DiagnosticRejection prepare(DiagnosticBudget& b) override {
    ++c.prepares; c.worker = std::this_thread::get_id();
    if (c.hook) c.hook("prepare", b);
    return c.prepare_reason;
  }
  DiagnosticRejection sample(DiagnosticBudget& b, DiagnosticObservation& out) override {
    ++c.samples;
    if (c.hook) c.hook("read", b);
    if (c.hook) c.hook("hash", b);
    out = observation;
    if (c.mutate) c.mutate(out);
    return c.sample_reason;
  }
  bool close() noexcept override { ++c.closes; return c.close_ok; }
};
struct Factory final : DiagnosticWorkFactory {
  Control& c; DiagnosticObservation observation;
  Factory(Control& control, DiagnosticObservation value) : c(control), observation(value) {}
  ~Factory() override { c.factory_thread = std::this_thread::get_id(); ++c.factory_destroys; }
  std::unique_ptr<DiagnosticWork> create(DiagnosticBudget& b) override {
    ++c.creates;
    if (c.hook) c.hook("factory", b);
    if (c.null_work) return {};
    return std::make_unique<Work>(c, observation);
  }
};
std::unique_ptr<DiagnosticWorkFactory> factory(Control& c, const Fixture& f) {
  return std::make_unique<Factory>(c, f.observation);
}
template<class Predicate> void eventually(Predicate predicate) {
  const auto until = Clock::now()+3s;
  while (!predicate()) { CHECK(Clock::now() < until); std::this_thread::sleep_for(100us); }
}
DiagnosticCompletion collect(DiagnosticWorker& worker) {
  DiagnosticCompletion result;
  eventually([&] { CHECK(worker.status().reason == Reason::none); return worker.take(result); });
  return result;
}
void no_result(DiagnosticWorker& worker) {
  DiagnosticCompletion result; result.bytes.fill(255); result.gates = {1,1};
  CHECK(!worker.take(result)); CHECK(result.gates.unknown == 0 && result.gates.violated == 0);
  CHECK(std::all_of(result.bytes.begin(), result.bytes.end(), [](auto b) { return b == 0; }));
}
void stopped(DiagnosticWorker& w, Reason why, bool close_ok = true) {
  CHECK(w.wait_stopped_until(Clock::now()+3s) == close_ok);
  const auto s = w.status(); CHECK(s.phase == Phase::stopped && s.joined);
  CHECK(s.reason == why && s.cleanup_verified == close_ok);
  no_result(w); w.cancel(); w.peer_lost(); w.lifecycle({9,9,9,9});
  CHECK(w.status().reason == why);
}
struct Block {
  std::mutex mutex; std::condition_variable wake; bool entered{}, released{};
  void hold() {
    std::unique_lock lock(mutex); entered = true; wake.notify_all();
    CHECK(wake.wait_for(lock, 3s, [&] { return released; }));
  }
  void wait() { std::unique_lock lock(mutex); CHECK(wake.wait_for(lock, 3s, [&] { return entered; })); }
  void release() { std::lock_guard lock(mutex); released = true; wake.notify_all(); }
};
}
int main(int argc, char** argv) {
  CHECK(argc == 2); const std::string mode = argv[1];
  Fixture f; Control c; FakeClock clock;
  if (mode == "stable") {
    DiagnosticWorker w(f.expectation, factory(c,f), clock);
    no_result(w);
    for (int i=1;i<=100;++i) {
      f.request.sequence = i; CHECK(w.submit(f.request,{})); auto out = collect(w);
      CHECK(out.bytes[8] == 1 && out.bytes[9] == 2 && out.bytes[10] == 1 && out.bytes[11] == 1);
      CHECK(out.bytes[32] == i && out.gates.unknown == (1u<<admission_condition_count)-1);
      CHECK(out.gates.violated == 0); no_result(w);
    }
    w.cancel(); stopped(w,Reason::cancelled);
    CHECK(c.creates == 1 && c.prepares == 1 && c.samples == 100 && c.closes == 1 && c.destroys == 1);
    CHECK(c.worker != std::this_thread::get_id() && c.worker == c.destroy_thread && c.worker == c.factory_thread);
    CHECK(!w.submit(f.request,{}));
  } else if (mode == "preparation") {
    c.hook = [&](const auto& phase, auto& b) {
      CHECK(b.checkpoint());
      CHECK(b.remaining() == (phase == "factory" ? 5s : phase == "prepare" ? 4s : phase == "read" ? 3s : 2s));
      clock.add(1s);
    };
    DiagnosticWorker w(f.expectation,factory(c,f),clock); CHECK(w.submit(f.request,{})); collect(w);
    w.cancel(); stopped(w,Reason::cancelled);
  } else if (mode.compare(0,9,"deadline_") == 0) {
    const auto target = mode.substr(9);
    c.hook = [&](const auto& phase, auto& b) {
      if (phase == target) { clock.add(5s); CHECK(!b.checkpoint()); CHECK(b.remaining() == 0s); }
    };
    DiagnosticWorker w(f.expectation,factory(c,f),clock); CHECK(w.submit(f.request,{}));
    stopped(w,Reason::deadline);
    CHECK(c.closes == 1 && c.destroys == 1);
    CHECK(c.prepares == (target == "factory" ? 0 : 1));
    CHECK(c.samples == (target == "factory" || target == "prepare" ? 0 : 1));
  } else if (mode == "cumulative") {
    c.hook = [&](const auto&, auto&) { clock.add(1300ms); };
    DiagnosticWorker w(f.expectation,factory(c,f),clock); CHECK(w.submit(f.request,{})); stopped(w,Reason::deadline);
  } else if (mode == "revalidation") {
    c.hook = [&](const auto& phase, auto&) { if (phase == "hash") clock.add(c.samples == 1 ? 4999ms : 2s); };
    DiagnosticWorker w(f.expectation,factory(c,f),clock); CHECK(w.submit(f.request,{})); collect(w);
    clock.add(20s); f.request.sequence = 2; CHECK(w.submit(f.request,{})); stopped(w,Reason::deadline);
    CHECK(c.prepares == 1 && c.samples == 2);
  } else if (mode == "publication") {
    DiagnosticWorker w(f.expectation,factory(c,f),clock); CHECK(w.submit(f.request,{}));
    eventually([&] { return w.status().phase == Phase::ready; });
    clock.add(5s); no_result(w); stopped(w,Reason::deadline);
  } else if (mode == "cancellation" || mode == "late_result") {
    for (const auto* target : {"factory","prepare","read","hash"}) {
      Control control; Block block;
      control.hook = [&](const auto& phase, auto& b) {
        if (phase == target) { block.hold(); CHECK(!b.checkpoint()); }
      };
      DiagnosticWorker w(f.expectation,factory(control,f),clock); CHECK(w.submit(f.request,{})); block.wait();
      if (mode == "cancellation") w.cancel(); else { clock.add(5s); CHECK(w.status().reason == Reason::deadline); }
      no_result(w); CHECK(!w.wait_stopped_until(Clock::now()+1ms));
      CHECK(!w.status().cleanup_verified && !w.status().joined && control.closes == 0 && control.destroys == 0);
      block.release(); stopped(w,mode == "cancellation" ? Reason::cancelled : Reason::deadline);
      CHECK(control.closes == 1 && control.destroys == 1);
    }
  } else if (mode == "cleanup_failure") {
    c.close_ok = false; c.sample_reason = Reason::peer_lost;
    DiagnosticWorker w(f.expectation,factory(c,f),clock); CHECK(w.submit(f.request,{})); stopped(w,Reason::peer_lost,false);
    CHECK(c.destroys == 1 && c.closes == 1);
  } else if (mode == "exceptions") {
    for (const auto* target : {"factory","prepare","read","hash"}) {
      Control control;
      control.hook = [&](const auto& phase, auto&) { if (phase == target) throw std::runtime_error("injected"); };
      DiagnosticWorker w(f.expectation,factory(control,f),clock); CHECK(w.submit(f.request,{})); stopped(w,Reason::unavailable);
      CHECK(control.closes == (std::string(target) == "factory" ? 0 : 1));
      CHECK(control.destroys == control.closes && control.factory_destroys == 1);
    }
    c.null_work = true; DiagnosticWorker w(f.expectation,factory(c,f),clock);
    CHECK(w.submit(f.request,{})); stopped(w,Reason::unavailable); CHECK(c.closes == 0);
  } else if (mode == "failures") {
    for (int stage=0;stage<2;++stage) for (int r=1;r<=10;++r) {
      Control control; const auto why = r == 10 ? static_cast<Reason>(255) : static_cast<Reason>(r);
      (stage == 0 ? control.prepare_reason : control.sample_reason) = why;
      DiagnosticWorker w(f.expectation,factory(control,f),clock); CHECK(w.submit(f.request,{}));
      stopped(w,r == 10 ? Reason::protocol : why); CHECK(control.samples == stage && control.closes == 1);
    }
  } else if (mode == "correlation") {
    for (int which=0;which<5;++which) {
      Control control; Fixture t; DiagnosticWorker w(t.expectation,factory(control,t),clock);
      CHECK(w.submit(t.request,{})); collect(w);
      t.request.sequence = 2;
      if (which == 0) t.request.sequence = 1;
      if (which == 1) t.request.sequence = 3;
      if (which == 2) t.request.sequence = UINT64_MAX;
      if (which == 3) t.request.challenge[0] ^= 1;
      if (which == 4) t.request.challenge.fill(0);
      CHECK(!w.submit(t.request,{})); stopped(w,Reason::protocol); CHECK(control.samples == 1);
    }
  } else if (mode == "overlap") {
    Block block; c.hook = [&](const auto& phase, auto&) { if (phase == "read") block.hold(); };
    DiagnosticWorker w(f.expectation,factory(c,f),clock); CHECK(w.submit(f.request,{})); block.wait();
    CHECK(!w.submit(f.request,{})); block.release(); stopped(w,Reason::protocol);
  } else if (mode == "identity") {
    for (int field=0;field<9;++field) {
      Control control;
      control.mutate = [&](auto& o) {
        if (control.samples != 2) return;
        auto& r = o.inventory;
        switch(field) {
          case 0: ++r.process.pid; break;
          case 1: ++r.process.birth_ns; break;
          case 2: ++r.process.nonce[0]; break;
          case 3: ++r.file_objects[0]; break;
          case 4: ++r.classified_images[0]; break;
          case 5: ++r.loader_revision; break;
          case 6: ++r.application_images; break;
          case 7: ++r.platform_images; break;
          case 8: ++r.policy_evidence[0]; break;
        }
      };
      DiagnosticWorker w(f.expectation,factory(control,f),clock); f.request.sequence = 1;
      CHECK(w.submit(f.request,{})); collect(w); f.request.sequence = 2;
      CHECK(w.submit(f.request,{})); stopped(w,field == 8 ? Reason::protocol : Reason::identity_changed);
      f.request.sequence = 3; CHECK(!w.submit(f.request,{})); CHECK(control.samples == 2);
    }
  } else if (mode == "lifecycle") {
    for (int field=0;field<4;++field) {
      Fixture t; Control control; Block block; t.observation.epochs = {1,2,3,4};
      auto expected = t.observation.epochs, changed = expected;
      auto* value = field == 0 ? &changed.host : field == 1 ? &changed.pine : field == 2 ? &changed.vu : &changed.gs;
      ++*value;
      control.hook = [&](const auto& phase, auto&) { if (phase == "hash") block.hold(); };
      DiagnosticWorker w(t.expectation,factory(control,t),clock); CHECK(w.submit(t.request,expected)); block.wait();
      w.lifecycle(expected); CHECK(w.status().reason == Reason::none); w.lifecycle(changed); w.lifecycle(expected);
      block.release(); stopped(w,Reason::lifecycle);
    }
    c.mutate = [](auto& o) { o.epochs = {1,2,3,4}; };
    DiagnosticWorker w(f.expectation,factory(c,f),clock); CHECK(w.submit(f.request,{})); stopped(w,Reason::lifecycle);
  } else if (mode == "peer") {
    DiagnosticWorker w(f.expectation,factory(c,f),clock); CHECK(w.submit(f.request,{})); collect(w);
    w.peer_lost(); stopped(w,Reason::peer_lost);
  } else if (mode == "gates") {
    for (unsigned field=0;field<=admission_condition_count;++field) for (const auto fact : {AdmissionFact::unknown,AdmissionFact::violated}) {
      Fixture t; Control control; t.observation.epochs = {1,2,3,4}; t.observation.facts.fill(AdmissionFact::satisfied);
      if (field < admission_condition_count) t.observation.facts[field] = fact;
      DiagnosticWorker w(t.expectation,factory(control,t),clock); CHECK(w.submit(t.request,t.observation.epochs));
      auto out = collect(w); const auto bit = field < admission_condition_count ? 1u<<field : 0;
      CHECK(out.gates.unknown == (fact == AdmissionFact::unknown ? bit : 0));
      CHECK(out.gates.violated == (fact == AdmissionFact::violated ? bit : 0));
      w.cancel(); stopped(w,Reason::cancelled);
    }
    // Claims of satisfied gates without VM epochs cannot enter the mailbox.
    f.observation.facts.fill(AdmissionFact::satisfied);
    DiagnosticWorker w(f.expectation,factory(c,f),clock); CHECK(w.submit(f.request,{})); stopped(w,Reason::protocol);
  } else if (mode == "clock") {
    for (int stage=0;stage<3;++stage) {
      Control control; FakeClock fake;
      control.hook = [&](const auto& phase, auto&) { if (stage == 0 && phase == "hash") fake.add(-1ns); };
      DiagnosticWorker w(f.expectation,factory(control,f),fake); f.request.sequence = 1;
      if (stage == 2) fake.ticks = std::chrono::duration_cast<std::chrono::nanoseconds>(Clock::time_point::max().time_since_epoch()).count();
      CHECK(w.submit(f.request,{}) == (stage != 2));
      if (stage == 1) { collect(w); fake.add(-1ns); f.request.sequence = 2; CHECK(!w.submit(f.request,{})); }
      stopped(w,Reason::unavailable);
    }
  } else if (mode == "boundaries") {
    for (int which=0;which<9;++which) {
      Control control; Fixture t; DiagnosticEpochs epochs;
      if (which == 0) t.expectation = {};
      if (which == 2) t.request.sequence = 0;
      if (which == 3) t.request.sequence = 2;
      if (which == 4) t.request.challenge = {};
      if (which == 5) epochs = {1,0,0,0};
      if (which == 6) epochs = {1,2,3,UINT64_MAX};
      DiagnosticWorker w(t.expectation,which == 1 ? nullptr : factory(control,t),clock);
      if (which == 7) w.cancel();
      if (which == 8) w.lifecycle({1,0,0,0});
      CHECK(!w.submit(t.request,epochs));
      stopped(w,which < 2 ? Reason::configuration : which < 5 ? Reason::protocol : which == 7 ? Reason::cancelled : Reason::lifecycle);
      CHECK(control.creates == 0);
    }
  } else if (mode == "race") {
    for (int i=0;i<100;++i) {
      Control control; DiagnosticWorker w(f.expectation,factory(control,f),clock);
      CHECK(w.submit(f.request,{}));
      std::thread cancellation([&] { w.cancel(); });
      DiagnosticCompletion out; w.take(out); cancellation.join();
      no_result(w); stopped(w,Reason::cancelled);
      CHECK(control.closes == control.destroys && control.closes <= 1);
    }
  } else if (mode == "destruction") {
    Block block; c.hook = [&](const auto& phase, auto&) { if (phase == "hash") block.hold(); };
    auto w = std::make_unique<DiagnosticWorker>(f.expectation,factory(c,f),clock);
    CHECK(w->submit(f.request,{})); block.wait(); w->cancel();
    std::atomic<bool> deleting{}, deleted{};
    std::thread owner([owned=std::move(w),&deleting,&deleted]() mutable { deleting = true; owned.reset(); deleted = true; });
    eventually([&] { return deleting.load(); });
    CHECK(!deleted && c.destroys == 0); block.release(); owner.join();
    CHECK(deleted && c.closes == 1 && c.destroys == 1);
  } else { CHECK(false); }
  return 0;
}
