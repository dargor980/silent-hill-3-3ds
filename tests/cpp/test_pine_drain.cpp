#include "check.hpp"
#include "sh3_observer/pine_drain.hpp"
#include <functional>
#include <string>
#include <thread>
#include <vector>
using namespace sh3::observer;
using State=PineDrain::State;
using Clock=PineDrain::Clock;
struct Source final : BarrierSource {
  CooperativeGate gate;
  bool expired=false;
  CooperativeGate::Closure close(Clock::time_point deadline) noexcept override {
    return gate.close(expired ? Clock::now() : deadline);
  }
};
struct Fixture {
  CpuBoundary cpu;
  Source source;
  PineDrain drain{cpu,source};
  PineDrain::Identity identity{7,9};
  Fixture() { cpu.set_online(true); }
  auto request(std::uint64_t id=1) { return PineDrain::Request{id,identity,Clock::now()+std::chrono::seconds(5)}; }
  State step() { auto b=cpu.enter(); CHECK(b.valid()); return drain.step(true,identity); }
};
void submit() {
  Fixture f; CHECK(!f.drain.active()); CHECK(f.step()==State::idle);
  CHECK(f.drain.retire().state==State::idle); CHECK(!f.drain.cancel(1));
  CHECK(!f.drain.complete(true,f.identity));
  auto r=f.request(); r.id=0; CHECK(!f.drain.submit(r));
  r=f.request(); r.identity.vm=0; CHECK(!f.drain.submit(r));
  r=f.request(); r.identity.server=0; CHECK(!f.drain.submit(r));
  r=f.request(); r.deadline=Clock::now(); CHECK(!f.drain.submit(r));
  CHECK(f.drain.submit(f.request())); CHECK(!f.drain.submit(f.request(2)));
  CHECK(f.drain.status().id==1); CHECK(f.drain.status().state==State::queued);
  CHECK(f.source.gate.enter()); CHECK(f.drain.cancel(1)); CHECK(f.drain.retire().id==1);
  CHECK(!f.drain.submit(f.request())); CHECK(f.drain.submit(f.request(2)));
}
void complete() {
  Fixture f; CHECK(f.drain.submit(f.request())); auto b=f.cpu.enter();
  CHECK(f.drain.step(true,f.identity)==State::held); CHECK(!f.source.gate.enter());
  CHECK(f.drain.retire().state==State::idle); CHECK(!f.source.gate.enter());
  CHECK(f.drain.complete(true,f.identity)); CHECK(!f.drain.cancel(1));
  CHECK(f.drain.step(false,{})==State::completed); CHECK(!f.source.gate.enter());
  auto r=f.drain.retire(); CHECK(r.id==1 && r.state==State::completed);
  CHECK(f.source.gate.enter()); CHECK(!f.drain.active());
}
void draining() {
  Fixture f; auto work=f.source.gate.enter(); int writes=0;
  std::vector<std::function<void()>> queue;
  queue.emplace_back([work,&writes] { ++writes; }); work={};
  CHECK(f.drain.submit(f.request())); CHECK(f.step()==State::draining);
  CHECK(!f.source.gate.enter());
  { auto active=f.cpu.activity(); queue.front()(); queue.clear(); }
  CHECK(writes==1); CHECK(f.step()==State::held);
  auto root=f.cpu.enter(); CHECK(f.drain.complete(true,f.identity));
  CHECK(f.drain.retire().state==State::completed);
}
void discarded() {
  Fixture f; std::vector<CooperativeGate::Work> retained{f.source.gate.enter()};
  CHECK(f.drain.submit(f.request())); CHECK(f.step()==State::draining);
  retained.clear(); CHECK(f.step()==State::held);
}
void cancel() {
  Fixture f; auto work=f.source.gate.enter(); CHECK(f.drain.submit(f.request()));
  CHECK(f.step()==State::draining); CHECK(!f.drain.cancel(2));
  CHECK(f.drain.cancel(1)); CHECK(!f.drain.cancel(1));
  CHECK(f.step()==State::cancelled); CHECK(!f.source.gate.enter());
  CHECK(f.drain.retire().state==State::cancelled); CHECK(f.source.gate.enter());
  CHECK(f.drain.submit(f.request(2))); CHECK(f.step()==State::draining);
  work={}; CHECK(f.step()==State::held);
}
void timeout() {
  Fixture f; auto r=f.request(); r.deadline=Clock::now()+std::chrono::milliseconds(20);
  CHECK(f.drain.submit(r)); std::this_thread::sleep_until(r.deadline);
  CHECK(f.step()==State::timed_out); CHECK(f.drain.retire().state==State::timed_out);
  f.source.expired=true; CHECK(f.drain.submit(f.request(2)));
  CHECK(f.step()==State::timed_out); CHECK(!f.source.gate.enter());
  CHECK(f.drain.retire().state==State::timed_out); CHECK(f.source.gate.enter());
}
void identity() {
  for(unsigned i=0;i<5;++i) {
    Fixture f; CHECK(f.drain.submit(f.request())); CHECK(f.step()==State::held);
    auto next=f.identity; if(i==0)next.vm=0; if(i==1)next.server=0;
    if(i==2)++next.vm; if(i==3)++next.server;
    auto b=f.cpu.enter(); CHECK(!f.drain.complete(i!=4,next));
    CHECK(f.drain.status().state==State::invalidated); CHECK(!f.source.gate.enter());
    CHECK(f.drain.retire().state==State::invalidated); CHECK(f.source.gate.enter());
  }
}
void boundary() {
  Fixture f; CHECK(f.drain.submit(f.request()));
  CHECK(f.drain.step(true,f.identity)==State::invalidated); CHECK(f.source.gate.enter());
  CHECK(f.drain.retire().state==State::invalidated);
  CHECK(f.drain.submit(f.request(2))); CHECK(f.step()==State::held);
  auto b=f.cpu.enter(); { auto nested=f.cpu.enter(); CHECK(!nested.valid()); }
  CHECK(!f.drain.complete(true,f.identity)); CHECK(!f.source.gate.enter());
}
void contention() {
  Fixture f; auto owner=f.source.gate.close(Clock::now()+std::chrono::seconds(5));
  CHECK(f.drain.submit(f.request())); CHECK(f.step()==State::rejected);
  CHECK(f.drain.retire().state==State::rejected); CHECK(!f.source.gate.enter());
  CHECK(owner.poll()==CooperativeGate::State::held);
}
void shutdown() {
  CpuBoundary cpu; cpu.set_online(true); Source source; auto work=source.gate.enter();
  { PineDrain drain(cpu,source); CHECK(drain.submit({1,{1,1},Clock::now()+std::chrono::seconds(5)}));
    auto root=cpu.enter(); CHECK(drain.step(true,{1,1})==State::draining); CHECK(!source.gate.enter()); }
  CHECK(source.gate.enter()); // The earlier Work is still alive; no false completion.
}
int main(int argc,char** argv) {
  CHECK(argc==2); const std::string n=argv[1];
  if(n=="submit")submit(); else if(n=="complete")complete(); else if(n=="draining")draining();
  else if(n=="discarded")discarded(); else if(n=="cancel")cancel(); else if(n=="timeout")timeout();
  else if(n=="identity")identity(); else if(n=="boundary")boundary(); else if(n=="contention")contention();
  else if(n=="shutdown")shutdown(); else CHECK(false);
}
