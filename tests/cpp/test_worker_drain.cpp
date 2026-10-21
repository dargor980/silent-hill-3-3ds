#include "check.hpp"
#include "sh3_observer/worker_drain.hpp"
#include <atomic>
#include <functional>
#include <limits>
#include <string>
#include <thread>
#include <vector>
using namespace sh3::observer;
using Clock = PineDrain::Clock;
using State = PineDrain::State;
using Status = WorkerControl::Status;
using Progress = EffectDrainPort::Progress;
using Token = WorkerControl::Token;
struct Source final : BarrierSource {
  CooperativeGate gate;
  CooperativeGate::Closure close(Clock::time_point deadline) noexcept override { return gate.close(deadline); }
};
struct Port final : WorkerPort {
  ControlWakeup wake;
  WorkerControl control{wake};
  Token owned{};
  bool reject{};
  unsigned requests{}, releases{};
  std::function<void()> on_request, on_release;
  mutable std::function<void()> on_status;
  WorkerControl::Lifecycle lifecycle() const noexcept override { return control.lifecycle(); }
  bool request(Token t) noexcept override {
    ++requests;
    if(on_request)on_request();
    if(reject || owned.id || !control.request(t))return false;
    owned=t;return true;
  }
  Status status(Token t) const noexcept override {
    if(on_status)on_status();
    return control.status(t);
  }
  void release(Token t) noexcept override {
    CHECK(t==owned);if(on_release)on_release();
    control.release(t);owned={};++releases;
  }
  void ack() { CHECK(control.acknowledge(owned)); }
};
struct Fixture {
  CpuBoundary cpu;
  Source source;
  Port vu,gs;
  WorkerDrain workers;
  RetainedDrain drain;
  PineDrain::Identity identity{7,9};
  std::vector<int> released;
  explicit Fixture(std::uint32_t budget=WorkerControl::max_request_id)
      : workers(vu,gs,budget),drain(cpu,source,workers) {
    cpu.set_online(true);CHECK(vu.control.start(11));CHECK(gs.control.start(17));
    gs.on_request=[&] { CHECK(vu.control.status(vu.owned)==Status::held); };
    gs.on_release=[&] {CHECK(!source.gate.enter());released.push_back(2);};
    vu.on_release=[&] {CHECK(!source.gate.enter());CHECK(!gs.owned.id);released.push_back(1);};
  }
  ~Fixture() { drain.cancel(drain.status().id);drain.retire(); }
  auto request(std::uint64_t id=1) { return PineDrain::Request{id,identity,Clock::now()+std::chrono::seconds(2)}; }
  State step() {auto b=cpu.enter();CHECK(b.valid());return drain.step(true,identity);}
  void phase(int p) {
    CHECK(drain.submit(request()));
    if(p==0)return;
    CHECK(step()==State::draining);CHECK(vu.requests==1 && gs.requests==0);
    if(p==1)return;
    vu.ack();CHECK(step()==State::draining);CHECK(gs.requests==1);
    if(p==2)return;
    gs.ack();CHECK(step()==State::held);
  }
  void retired(State expected,int phase) {
    CHECK(drain.retire().state==expected);CHECK(source.gate.enter());
    CHECK(!vu.owned.id && !gs.owned.id);
    CHECK(vu.releases==(phase>0?1u:0u));CHECK(gs.releases==(phase>1?1u:0u));
    CHECK(released==(phase>1?std::vector<int>{2,1}:phase>0?std::vector<int>{1}:std::vector<int>{}));
  }
};
void sequence() {
  Fixture f;auto prior=f.source.gate.enter();CHECK(f.drain.submit(f.request()));
  CHECK(f.step()==State::draining && !f.drain.effects_started());CHECK(f.vu.requests==0);
  prior={};CHECK(f.step()==State::draining);CHECK(f.vu.requests==1 && f.gs.requests==0);
  for(int i=0;i<4;++i)CHECK(f.step()==State::draining);
  f.vu.ack();CHECK(f.step()==State::draining);CHECK(f.gs.requests==1);
  for(int i=0;i<4;++i)CHECK(f.step()==State::draining);
  f.gs.ack();CHECK(f.step()==State::held);CHECK(!f.source.gate.enter());
  {auto b=f.cpu.enter();CHECK(f.drain.complete(true,f.identity));}
  f.retired(State::completed,3);
}
void cancel() {
  for(int p=0;p<4;++p){Fixture f;f.phase(p);CHECK(!f.drain.cancel(2));CHECK(f.drain.cancel(1));f.retired(State::cancelled,p);}
}
void rejection() {
  for(int which=0;which<2;++which){Fixture f;(which==0?f.vu:f.gs).reject=true;
    CHECK(f.drain.submit(f.request()));
    if(which){CHECK(f.step()==State::draining);f.vu.ack();}
    CHECK(f.step()==State::rejected);f.retired(State::rejected,which);}
}
void offline() {
  for(int which=0;which<2;++which){Fixture f;auto& port=which?f.gs:f.vu;
    CHECK(port.control.stop(port.lifecycle().generation)==WorkerControl::StopResult::stopped);
    CHECK(f.drain.submit(f.request()));CHECK(f.step()==State::rejected);f.retired(State::rejected,0);
    CHECK(!f.vu.requests && !f.gs.requests);}
}
void generations() {
  for(int p=1;p<3;++p){Fixture f;f.phase(p);
    auto& port=p==1?f.vu:f.gs;auto t=port.owned;
    CHECK(port.control.stop(t.generation)==WorkerControl::StopResult::stopped);
    CHECK(port.control.start(t.generation+1));
    CHECK(f.step()==State::rejected);f.retired(State::rejected,p);}
  Fixture f;f.phase(1);CHECK(f.gs.control.stop(17)==WorkerControl::StopResult::stopped);
  CHECK(f.gs.control.start(18));f.vu.ack();CHECK(f.step()==State::rejected);
  f.retired(State::rejected,1);CHECK(f.gs.requests==0);
}
void lost_token() {
  for(int p=1;p<4;++p)for(int which=0;which<(p>1?2:1);++which){Fixture f;f.phase(p);
    auto& port=which?f.gs:f.vu;CHECK(port.control.release(port.owned));
    CHECK(f.step()==State::rejected);f.retired(State::rejected,p);}
}
void epochs() {
  for(int p=1;p<4;++p)for(int which=0;which<4;++which){Fixture f;f.phase(p);
    {auto b=f.cpu.enter();auto id=f.identity;
      if(which==0){++id.vm;}
      if(which==1){++id.server;}
      if(which==3){auto a=f.cpu.activity();}
      CHECK(f.drain.step(which!=2,id)==State::invalidated);}
    f.retired(State::invalidated,p);}
}
void timeout() {
  for(int p=0;p<4;++p){Fixture f;auto r=f.request();r.deadline=Clock::now()+std::chrono::milliseconds(35);
    CHECK(f.drain.submit(r));
    if(p>0)CHECK(f.step()==State::draining);
    if(p>1){f.vu.ack();CHECK(f.step()==State::draining);}
    if(p>2){f.gs.ack();CHECK(f.step()==State::held);}
    std::this_thread::sleep_until(r.deadline);CHECK(f.step()==State::timed_out);f.retired(State::timed_out,p);}
}
void tickets() {
  Fixture f;const auto large=std::uint64_t(1)<<40;
  CHECK(f.drain.submit(f.request(large)));CHECK(f.step()==State::draining);
  CHECK(f.vu.owned.id==1);CHECK(f.drain.cancel(large));f.retired(State::cancelled,1);
  CHECK(f.drain.submit(f.request(std::numeric_limits<std::uint64_t>::max())));
  CHECK(f.step()==State::draining);CHECK(f.vu.owned.id==2);
  f.workers.begin(f.request(large+1));f.workers.release(large+1);
  CHECK(f.vu.owned.id==2);CHECK(f.workers.poll(large+1)==Progress::rejected);
}
void exhaustion() {
  for(std::uint32_t budget:{0u,1u,2u}){Fixture f(budget);
    for(std::uint64_t id=1;id<=budget;++id){CHECK(f.drain.submit(f.request(id)));
      CHECK(f.step()==State::draining);CHECK(f.vu.owned.id==id);CHECK(f.drain.cancel(id));f.drain.retire();}
    CHECK(f.drain.submit(f.request(budget+1)));CHECK(f.step()==State::rejected);
    CHECK(f.vu.requests==budget && f.gs.requests==0);}
}
void restart() {
  Fixture f;f.phase(3);CHECK(f.drain.cancel(1));f.retired(State::cancelled,3);
  CHECK(f.vu.control.stop(11)==WorkerControl::StopResult::stopped);CHECK(f.vu.control.start(12));
  CHECK(f.gs.control.stop(17)==WorkerControl::StopResult::stopped);CHECK(f.gs.control.start(18));
  CHECK(f.drain.submit(f.request(2)));CHECK(f.step()==State::draining);CHECK((f.vu.owned==Token{12,2}));
  f.vu.ack();CHECK(f.step()==State::draining);CHECK((f.gs.owned==Token{18,2}));
}
void revalidation() {
  Fixture f;f.phase(1);f.vu.ack();
  f.gs.on_request=[&]{CHECK(f.vu.control.release(f.vu.owned));};
  CHECK(f.step()==State::rejected);f.retired(State::rejected,2);
}
void conflict() {
  Fixture f;Token diagnostic{11,7};CHECK(f.vu.request(diagnostic));CHECK(f.vu.control.release(diagnostic));f.vu.owned={};
  CHECK(f.drain.submit(f.request()));CHECK(f.step()==State::rejected);f.retired(State::rejected,0);
  CHECK(f.vu.control.status(diagnostic)==Status::released);
}
void acknowledgement_race() {
  for(int which=0;which<2;++which)for(int i=0;i<150;++i){Fixture f;f.phase(which?2:1);
    auto& port=which?f.gs:f.vu;const auto token=port.owned;
    std::atomic_bool ready=false,go=false;
    std::thread worker([&]{ready=true;while(!go.load())std::this_thread::yield();port.control.acknowledge(token);});
    while(!ready.load()){std::this_thread::yield();}
    go=true;
    CHECK(f.drain.cancel(1));f.drain.retire();worker.join();
    CHECK(port.control.status(token)==Status::released);CHECK(f.source.gate.enter());}
}
void dependency() {
  Fixture f;std::atomic_bool gs_space=false,gs_consumed=false,vu_effect=false,vu_done=false,quit=false;
  std::atomic_uint gs_effects=0;
  // One full synthetic GS slot: VU cannot finish until GS consumes it.
  std::thread gs([&]{
    while(!quit.load()){
      auto t=f.gs.control.pending(17);
      if(t.id && vu_done.load() && !vu_effect.load()){if(f.gs.control.acknowledge(t))while(f.gs.control.status(t)==Status::held)std::this_thread::yield();}
      else {if(!gs_consumed.exchange(true)){++gs_effects;gs_space=true;}
        if(vu_effect.exchange(false))++gs_effects;}
      std::this_thread::yield();
    }
  });
  std::thread vu([&]{
    while(!gs_space.load())std::this_thread::yield();
    vu_effect=true;vu_done=true;
    while(!quit.load()){
      auto t=f.vu.control.pending(11);
      if(t.id && f.vu.control.acknowledge(t))while(f.vu.control.status(t)==Status::held)std::this_thread::yield();
      std::this_thread::yield();
    }
  });
  CHECK(f.drain.submit(f.request()));auto end=Clock::now()+std::chrono::seconds(1);
  State state;
  do{CHECK(Clock::now()<end);state=f.step();std::this_thread::yield();}while(state==State::draining);
  CHECK(state==State::held && vu_done.load() && gs_effects==2);
  CHECK(f.drain.cancel(1));f.drain.retire();quit=true;vu.join();gs.join();
  CHECK(gs_consumed && gs_effects==2);CHECK(f.source.gate.enter());
}
void invalid_request() {
  for(int kind=0;kind<3;++kind){Fixture f;auto r=f.request();
    if(kind==0){r.identity.vm=0;}
    if(kind==1){r.identity.server=0;}
    if(kind==2){r.deadline=Clock::now();}
    f.workers.begin(r);CHECK(f.workers.poll(r.id)==Progress::rejected);CHECK(!f.vu.requests);
    f.workers.release(r.id);}
}
int main(int argc,char** argv) {
  CHECK(argc==2);const std::string n=argv[1];
  if(n=="sequence")sequence();else if(n=="cancel")cancel();else if(n=="rejection")rejection();
  else if(n=="offline")offline();else if(n=="generations")generations();else if(n=="lost_token")lost_token();
  else if(n=="epochs")epochs();else if(n=="timeout")timeout();else if(n=="tickets")tickets();
  else if(n=="exhaustion")exhaustion();else if(n=="restart")restart();else if(n=="revalidation")revalidation();
  else if(n=="conflict")conflict();else if(n=="acknowledgement_race")acknowledgement_race();
  else if(n=="dependency")dependency();else if(n=="invalid_request")invalid_request();else CHECK(false);
}
