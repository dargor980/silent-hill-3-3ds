#include "check.hpp"
#include "sh3_observer/retained_drain.hpp"
#include <functional>
#include <string>
#include <thread>
using namespace sh3::observer;
using State = RetainedDrain::State;
using Clock = PineDrain::Clock;
using Progress = EffectDrainPort::Progress;
struct Source final : BarrierSource {
  CooperativeGate gate;
  CooperativeGate::Closure close(Clock::time_point deadline) noexcept override {
    return gate.close(deadline);
  }
};
struct Port final : EffectDrainPort {
  unsigned begins{}, polls{}, releases{};
  std::uint64_t id{};
  Progress progress{Progress::pending};
  std::function<void()> on_begin, on_poll, on_release;
  void begin(PineDrain::Request request) noexcept override {
    CHECK(!id); id=request.id; ++begins;
    if(on_begin)on_begin();
  }
  Progress poll(std::uint64_t request_id) noexcept override {
    CHECK(id==request_id); ++polls;
    if(on_poll)on_poll();
    return progress;
  }
  void release(std::uint64_t request_id) noexcept override {
    CHECK(id==request_id); ++releases;
    if(on_release)on_release();
    id=0;
  }
};
struct Fixture {
  CpuBoundary cpu;
  Source source;
  Port port;
  RetainedDrain drain{cpu,source,port};
  RetainedDrain::Identity identity{7,9};
  Fixture() { cpu.set_online(true); }
  auto request(std::uint64_t id=1) {
    return RetainedDrain::Request{id,identity,Clock::now()+std::chrono::seconds(5)};
  }
  State step() { auto b=cpu.enter(); CHECK(b.valid()); return drain.step(true,identity); }
};
void submit() {
  Fixture f; CHECK(f.step()==State::idle); CHECK(!f.drain.active());
  CHECK(!f.drain.cancel(1)); CHECK(!f.drain.complete(true,f.identity));
  CHECK(f.drain.retire().state==State::idle);
  auto r=f.request(); r.id=0; CHECK(!f.drain.submit(r));
  r=f.request(); r.deadline=Clock::now(); CHECK(!f.drain.submit(r));
  CHECK(f.drain.submit(f.request())); CHECK(!f.drain.submit(f.request(2)));
  CHECK(f.drain.status().state==State::queued); CHECK(f.drain.status().id==1);
  CHECK(f.drain.cancel(1)); CHECK(f.drain.retire().state==State::cancelled);
  CHECK(!f.drain.submit(f.request())); CHECK(f.drain.submit(f.request(2)));
  CHECK(f.port.begins==0 && f.port.releases==0);
}
void phases() {
  Fixture f; auto work=f.source.gate.enter(); CHECK(f.drain.submit(f.request()));
  CHECK(f.step()==State::draining); CHECK(f.port.begins==0);
  CHECK(!f.source.gate.enter());
  { auto activity=f.cpu.activity(); work={}; }
  CHECK(f.step()==State::draining); CHECK(f.drain.effects_started());
  CHECK(f.port.begins==1 && f.port.polls==1); CHECK(!f.source.gate.enter());
  CHECK(f.step()==State::draining); CHECK(f.port.begins==1 && f.port.polls==2);
  CHECK(f.drain.retire().state==State::idle); CHECK(!f.source.gate.enter());
  f.port.progress=Progress::held; CHECK(f.step()==State::held);
  CHECK(!f.source.gate.enter()); CHECK(f.port.releases==0);
}
void complete() {
  Fixture f; f.port.progress=Progress::held;
  CHECK(f.drain.submit(f.request())); CHECK(f.step()==State::held);
  { auto b=f.cpu.enter(); CHECK(f.drain.complete(true,f.identity)); }
  CHECK(f.drain.status().state==State::completed); CHECK(f.drain.active());
  CHECK(!f.drain.cancel(1)); CHECK(f.step()==State::completed);
  CHECK(!f.source.gate.enter()); CHECK(f.port.releases==0);
  CHECK(f.drain.retire().state==State::completed); CHECK(f.port.releases==1);
  CHECK(f.source.gate.enter()); CHECK(!f.drain.active()); CHECK(!f.drain.effects_started());
  CHECK(f.drain.retire().state==State::idle); CHECK(f.port.releases==1);
}
void cancel() {
  for(int phase=0;phase<4;++phase) {
    Fixture f; auto work=f.source.gate.enter(); CHECK(f.drain.submit(f.request()));
    if(phase>0)CHECK(f.step()==State::draining);
    if(phase>1) { work={}; CHECK(f.step()==State::draining); }
    if(phase>2) { f.port.progress=Progress::held; CHECK(f.step()==State::held); }
    CHECK(!f.drain.cancel(2)); CHECK(f.drain.cancel(1)); CHECK(!f.drain.cancel(1));
    CHECK(f.step()==State::cancelled); if(phase>0)CHECK(!f.source.gate.enter());
    CHECK(f.drain.retire().state==State::cancelled);
    CHECK(f.port.releases==(phase>1?1u:0u)); CHECK(f.source.gate.enter());
  }
}
void rejection() {
  for(auto progress:{Progress::rejected,static_cast<Progress>(99)}) {
    Fixture f; f.port.progress=progress; CHECK(f.drain.submit(f.request()));
    CHECK(f.step()==State::rejected); CHECK(!f.source.gate.enter());
    CHECK(f.port.begins==1); CHECK(f.drain.retire().state==State::rejected);
    CHECK(f.port.releases==1); CHECK(f.source.gate.enter());
  }
  Fixture f; auto owner=f.source.gate.close(Clock::now()+std::chrono::seconds(5));
  CHECK(f.drain.submit(f.request())); CHECK(f.step()==State::rejected);
  CHECK(f.drain.retire().state==State::rejected); CHECK(f.port.begins==0);
  CHECK(!f.source.gate.enter()); CHECK(owner.poll()==CooperativeGate::State::held);
}
void invalidation() {
  for(int cause=0;cause<5;++cause) {
    Fixture f; f.port.progress=Progress::held;
    CHECK(f.drain.submit(f.request())); CHECK(f.step()==State::held);
    auto identity=f.identity; if(cause==0)++identity.vm; if(cause==1)++identity.server;
    if(cause==2)identity={};
    { auto b=f.cpu.enter();
      if(cause==4) { auto activity=f.cpu.activity(); }
      CHECK(!f.drain.complete(cause!=3,identity)); }
    CHECK(f.drain.status().state==State::invalidated); CHECK(!f.source.gate.enter());
    CHECK(f.drain.retire().state==State::invalidated); CHECK(f.port.releases==1);
  }
  Fixture f; CHECK(f.drain.submit(f.request()));
  f.port.on_poll=[&] { auto activity=f.cpu.activity(); };
  CHECK(f.step()==State::invalidated); CHECK(!f.source.gate.enter());
}
void timeout() {
  for(int phase=0;phase<3;++phase) {
    Fixture f; auto r=f.request(); r.deadline=Clock::now()+std::chrono::milliseconds(25);
    CHECK(f.drain.submit(r));
    if(phase==1)CHECK(f.step()==State::draining);
    if(phase==2)f.port.on_poll=[&] { std::this_thread::sleep_until(r.deadline); };
    if(phase<2)std::this_thread::sleep_until(r.deadline);
    CHECK(f.step()==State::timed_out); CHECK(f.drain.retire().state==State::timed_out);
    CHECK(f.port.releases==(phase>0?1u:0u)); CHECK(f.source.gate.enter());
  }
}
void reentry() {
  for(int callback=0;callback<2;++callback)for(int action=0;action<3;++action) {
    Fixture f; CHECK(f.drain.submit(f.request()));
    auto reenter=[&] {
      CHECK(!f.drain.submit(f.request(2))); CHECK(f.drain.retire().state==State::idle);
      if(action==0)CHECK(f.drain.step(true,f.identity)==State::invalidated);
      if(action==1)CHECK(f.drain.cancel(1));
      CHECK(f.drain.retire().state==State::idle); CHECK(f.port.releases==0);
    };
    if(callback==0)f.port.on_begin=reenter; else f.port.on_poll=reenter;
    const auto wanted=action==0?State::invalidated:action==1?State::cancelled:State::draining;
    CHECK(f.step()==wanted); CHECK(!f.source.gate.enter());
    f.port.on_begin={}; f.port.on_poll={};
    if(action==2)CHECK(f.drain.cancel(1));
    CHECK(f.drain.retire().id==1); CHECK(f.port.releases==1);
  }
}
void release_order() {
  Fixture f; CHECK(f.drain.submit(f.request())); CHECK(f.step()==State::draining);
  CHECK(f.drain.cancel(1));
  f.port.on_release=[&] {
    CHECK(f.drain.status().state==State::cancelled);
    CHECK(f.drain.effects_started()); CHECK(!f.source.gate.enter());
    CHECK(!f.drain.submit(f.request(2))); CHECK(f.drain.retire().state==State::idle);
    CHECK(f.drain.step(true,f.identity)==State::cancelled);
  };
  CHECK(f.drain.retire().id==1); CHECK(f.source.gate.enter());
  f.port.on_release={}; CHECK(f.drain.submit(f.request(2))); CHECK(!f.drain.cancel(1));
}
void shutdown() {
  for(bool started:{false,true}) {
    CpuBoundary cpu; cpu.set_online(true); Source source; Port port;
    { RetainedDrain drain(cpu,source,port);
      CHECK(drain.submit({1,{1,1},Clock::now()+std::chrono::seconds(5)}));
      if(started) { auto b=cpu.enter(); CHECK(drain.step(true,{1,1})==State::draining); }
    }
    CHECK(port.releases==(started?1u:0u)); CHECK(source.gate.enter());
  }
}
int main(int argc,char** argv) {
  CHECK(argc==2); const std::string n=argv[1];
  if(n=="submit")submit(); else if(n=="phases")phases(); else if(n=="complete")complete();
  else if(n=="cancel")cancel(); else if(n=="rejection")rejection(); else if(n=="invalidation")invalidation();
  else if(n=="timeout")timeout(); else if(n=="reentry")reentry();
  else if(n=="release_order")release_order(); else if(n=="shutdown")shutdown(); else CHECK(false);
}
