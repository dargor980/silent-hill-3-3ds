#include "delivery_fixture.hpp"
#include <algorithm>
#include <condition_variable>
#include <mutex>
#include <string>
#include <vector>
using namespace delivery_fixture;
namespace {
struct Sink final : DiagnosticDeliverySink {
  std::vector<std::uint8_t> bytes;
  std::function<void()> hook;
  std::size_t chunk{17};unsigned calls{};bool ok{true},oversize{};
  bool write(const std::uint8_t* p,std::size_t n,std::size_t& written,Clock::duration wait) noexcept override {
    CHECK(wait>0s && wait<=20ms);++calls;
    written=std::min(n,chunk);bytes.insert(bytes.end(),p,p+written);
    if(oversize)written=n+1;
    if(hook)hook();return ok;
  }
};
void deliver(DiagnosticWorker& w,Sink& sink,DiagnosticDeliveryResult expected){
  DiagnosticDeliveryResult r{};
  eventually([&]{r=deliver_diagnostic(w,sink);return r!=DiagnosticDeliveryResult::waiting;});CHECK(r==expected);
}
}
int main(int argc,char** argv){
  CHECK(argc==2);const std::string mode=argv[1];State s;FakeClock clock;
  if(mode=="stable"){
    DiagnosticWorker w(expectation(),factory(s),clock);
    CHECK(!w.delivery_checkpoint() && w.delivery_remaining()==0s);
    DiagnosticCompletion empty;CHECK(!w.take_for_delivery(empty));
    for(unsigned i=1;i<=100;++i){
      CHECK(w.submit_until(request(i),{},clock.now()+(i==1?5s:2s)));
      auto c=take(w);CHECK(c.bytes[8]==1 && s.samples==i && w.status().phase==Phase::delivering);
      CHECK(w.delivery_checkpoint() && w.delivery_remaining()==(i==1?5s:2s));
      std::this_thread::sleep_for(100us);CHECK(s.samples==i);
      CHECK(w.complete_delivery());CHECK(w.status().phase==Phase::idle);
    }
    w.cancel();stopped(w,Reason::cancelled);CHECK(s.prepares==1 && s.samples==100 && s.closes==1);
  }else if(mode=="expired"){
    for(auto offset:{-1ns,0ns}){
      State state;DiagnosticWorker w(expectation(),factory(state),clock);
      CHECK(!w.submit_until(request(),{},clock.now()+offset));stopped(w,Reason::deadline);CHECK(state.creates==0);
    }
  }else if(mode=="receive_cost"){
    auto start=clock.now();clock.add(3s);
    s.prepare_hook=[](auto& b){CHECK(b.remaining()==2s);};
    DiagnosticWorker w(expectation(),factory(s),clock);CHECK(w.submit_until(request(),{},start+5s));take(w);
    CHECK(w.delivery_remaining()==2s);CHECK(w.complete_delivery());
    start=clock.now();clock.add(1s);CHECK(w.submit_until(request(2),{},start+2s));take(w);
    CHECK(w.delivery_remaining()==1s);CHECK(w.complete_delivery());w.cancel();stopped(w,Reason::cancelled);
  }else if(mode=="future_limit"){
    DiagnosticWorker w(expectation(),factory(s),clock);
    for(unsigned i=1;i<=2;++i){CHECK(w.submit_until(request(i),{},clock.now()+30s));take(w);
      CHECK(w.delivery_remaining()==(i==1?5s:2s));CHECK(w.complete_delivery());}
    w.cancel();stopped(w,Reason::cancelled);
  }else if(mode=="external_cancel"){
    // The caller's flag changes during a real delivery call, not between steps.
    for(const std::size_t chunk:{0U,1U,293U,294U}){
      State state;DiagnosticWorker w(expectation(),factory(state),clock);Sink sink;
      std::atomic<bool> cancelled{};sink.chunk=chunk;sink.hook=[&]{cancelled=true;};
      CHECK(w.submit_until(request(),{},clock.now()+5s));
      DiagnosticDeliveryResult result{};
      eventually([&]{result=deliver_diagnostic(w,sink,cancelled);return result!=DiagnosticDeliveryResult::waiting;});
      CHECK(result==DiagnosticDeliveryResult::rejected && sink.calls==1 && sink.bytes.size()==chunk);
      CHECK(deliver_diagnostic(w,sink,cancelled)==DiagnosticDeliveryResult::rejected && sink.calls==1);
      stopped(w,Reason::cancelled);CHECK(state.samples==1 && state.closes==1);
    }
    State state;DiagnosticWorker w(expectation(),factory(state),clock);Sink sink;std::atomic<bool> cancelled{true};
    CHECK(deliver_diagnostic(w,sink,cancelled)==DiagnosticDeliveryResult::rejected && sink.calls==0);
    stopped(w,Reason::cancelled);CHECK(state.creates==0);
  }else if(mode=="partial"){
    DiagnosticWorker w(expectation(),factory(s),clock);Sink sink;
    CHECK(deliver_diagnostic(w,sink)==DiagnosticDeliveryResult::waiting && sink.calls==0);
    CHECK(w.submit_until(request(),{},clock.now()+5s));deliver(w,sink,DiagnosticDeliveryResult::complete);
    CHECK(sink.bytes.size()==diagnostic_response_size && sink.calls==18 && s.samples==1);
    CHECK(w.status().phase==Phase::idle);w.cancel();stopped(w,Reason::cancelled);
  }else if(mode=="cumulative"){
    s.prepare_hook=[&](auto&){clock.add(1s);};s.sample_hook=[&](auto&){clock.add(1s);};
    DiagnosticWorker w(expectation(),factory(s),clock);Sink sink;sink.hook=[&]{clock.add(1s);};
    CHECK(w.submit_until(request(),{},clock.now()+5s));deliver(w,sink,DiagnosticDeliveryResult::rejected);
    CHECK(sink.calls==3 && sink.bytes.size()==51);stopped(w,Reason::deadline);
  }else if(mode=="backpressure"){
    DiagnosticWorker w(expectation(),factory(s),clock);Sink sink;sink.chunk=0;sink.hook=[&]{clock.add(1s);};
    CHECK(w.submit_until(request(),{},clock.now()+5s));deliver(w,sink,DiagnosticDeliveryResult::rejected);
    CHECK(sink.calls==5 && sink.bytes.empty());stopped(w,Reason::deadline);
  }else if(mode=="sink_failure"){
    for(bool oversized:{false,true}){
      State state;DiagnosticWorker w(expectation(),factory(state),clock);Sink sink;
      sink.ok=oversized;sink.oversize=oversized;
      CHECK(w.submit_until(request(),{},clock.now()+5s));deliver(w,sink,DiagnosticDeliveryResult::rejected);
      CHECK(sink.calls==1);stopped(w,Reason::peer_lost);
    }
  }else if(mode=="last_byte"){
    for(const auto reason:{Reason::cancelled,Reason::peer_lost,Reason::lifecycle,Reason::deadline}){
      State state;DiagnosticWorker w(expectation(),factory(state),clock);Sink sink;sink.chunk=294;
      sink.hook=[&]{if(reason==Reason::cancelled)w.cancel();else if(reason==Reason::peer_lost)w.peer_lost();
        else if(reason==Reason::lifecycle)w.lifecycle({1,2,3,4});else clock.add(5s);};
      CHECK(w.submit_until(request(),{},clock.now()+5s));deliver(w,sink,DiagnosticDeliveryResult::rejected);
      CHECK(sink.bytes.size()==294 && sink.calls==1);stopped(w,reason);
    }
  }else if(mode=="confirmation"){
    for(unsigned which=0;which<3;++which){
      State state;DiagnosticWorker w(expectation(),factory(state),clock);
      if(which){CHECK(w.submit_until(request(),{},clock.now()+5s));if(which==2){take(w);CHECK(w.complete_delivery());}}
      CHECK(!w.complete_delivery());stopped(w,Reason::protocol);
    }
  }else if(mode=="overlap"){
    for(bool second_take:{false,true}){
      State state;DiagnosticWorker w(expectation(),factory(state),clock);CHECK(w.submit_until(request(),{},clock.now()+5s));take(w);
      if(second_take){DiagnosticCompletion c;c.bytes.fill(255);CHECK(!w.take_for_delivery(c));CHECK(c.bytes==DiagnosticBytes{});}
      else CHECK(!w.submit_until(request(2),{},clock.now()+2s));
      stopped(w,Reason::protocol);CHECK(state.samples==1);
    }
  }else if(mode=="mixed_modes"){
    for(unsigned which=0;which<4;++which){
      State state;DiagnosticWorker w(expectation(),factory(state),clock);DiagnosticCompletion c;
      if(which<2){CHECK(w.submit(request(),{}));
        if(which==0){eventually([&]{return w.take(c);});CHECK(!w.submit_until(request(2),{},clock.now()+2s));}
        else CHECK(!w.take_for_delivery(c));
      }else{CHECK(w.submit_until(request(),{},clock.now()+5s));
        if(which==2)CHECK(!w.take(c));else{take(w);CHECK(w.complete_delivery());CHECK(!w.submit(request(2),{}));}}
      stopped(w,Reason::protocol);
    }
  }else if(mode=="boundary"){
    for(auto delta:{4999999999ns,5000000000ns}){
      State state;DiagnosticWorker w(expectation(),factory(state),clock);CHECK(w.submit_until(request(),{},clock.now()+5s));take(w);
      clock.add(delta);const bool before=delta<5s;CHECK(w.complete_delivery()==before);
      if(before)w.cancel();stopped(w,before?Reason::cancelled:Reason::deadline);
    }
  }else if(mode=="clock"){
    DiagnosticWorker w(expectation(),factory(s),clock);CHECK(w.submit_until(request(),{},clock.now()+5s));take(w);
    clock.add(-1ns);CHECK(!w.delivery_checkpoint());stopped(w,Reason::unavailable);
  }else if(mode=="automatic_expiry"){
    DiagnosticWorker w(expectation(),factory(s));CHECK(w.submit_until(request(),{},Clock::now()+500ms));take(w);
    // No polling of state/budget/consumer: the worker itself must expire delivery.
    stopped(w,Reason::deadline);CHECK(s.samples==1 && s.closes==1);
  }else if(mode=="close_pending"){
    std::mutex mutex;std::condition_variable wake;bool entered=false,released=false;
    s.close_ok=false;s.close_hook=[&]{std::unique_lock lock(mutex);entered=true;wake.notify_all();CHECK(wake.wait_for(lock,3s,[&]{return released;}));};
    DiagnosticWorker w(expectation(),factory(s),clock);CHECK(w.submit_until(request(),{},clock.now()+5s));take(w);w.cancel();
    {std::unique_lock lock(mutex);CHECK(wake.wait_for(lock,3s,[&]{return entered;}));}
    CHECK(!w.wait_stopped_until(Clock::now()+1ms) && !w.status().joined);
    {std::lock_guard lock(mutex);released=true;wake.notify_all();}
    stopped(w,Reason::cancelled,false);CHECK(s.closes==1);
  }else if(mode=="race"){
    for(unsigned i=0;i<100;++i){
      State state;DiagnosticWorker w(expectation(),factory(state),clock);CHECK(w.submit_until(request(),{},clock.now()+5s));take(w);
      std::thread cancel([&]{w.cancel();});w.complete_delivery();cancel.join();stopped(w,Reason::cancelled);
      CHECK(state.samples==1 && state.closes==1);
    }
  }else CHECK(false);
}
