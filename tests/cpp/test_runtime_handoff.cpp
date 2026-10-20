#include "delivery_fixture.hpp"
#include "sh3_observer/runtime_diagnostic_handoff.hpp"
#include <semaphore>
#include <string>
using namespace delivery_fixture;
namespace {
RuntimeDiagnosticSnapshot snapshot(Clock::time_point deadline) {
  RuntimeDiagnosticSnapshot s;s.scope_id=7;s.deadline=deadline;s.epochs={1,2,3,4};
  for(auto c:{AdmissionCondition::cpu_thread,AdmissionCondition::cpu_boundary,AdmissionCondition::paused,
      AdmissionCondition::pine_excluded,AdmissionCondition::vu_drained,AdmissionCondition::gs_drained})
    s.facts[static_cast<std::size_t>(c)]=AdmissionFact::satisfied;
  return s;
}
struct Queue final : RuntimeDiagnosticQueue {
  FakeClock& clock;RuntimeRevocation generation;unsigned calls{};bool reject{};
  std::uint64_t id{};Clock::time_point deadline{};std::shared_ptr<RuntimeDiagnosticTicket> ticket;
  std::function<void()> hook;
  explicit Queue(FakeClock& c):clock(c){}
  std::shared_ptr<RuntimeDiagnosticTicket> queue_until(std::uint64_t i,Clock::time_point d) noexcept override {
    ++calls;id=i;deadline=d;if(hook)hook();if(reject)return {};
    ticket=make_runtime_diagnostic_ticket(generation,clock);return ticket;
  }
  void publish(){CHECK(ticket && ticket->publish(snapshot(deadline)));}
  void retire(){CHECK(ticket->retire());}
};
struct Sink final : DiagnosticDeliverySink {
  unsigned bytes{};
  bool write(const std::uint8_t*,std::size_t n,std::size_t& out,Clock::duration) noexcept override {
    out=std::min<std::size_t>(n,3);bytes+=out;return true;
  }
};
}
int main(int argc,char** argv){
  CHECK(argc==2);const std::string mode=argv[1];FakeClock clock;Queue queue(clock);
  const auto deadline=clock.now()+5s;
  auto h=std::make_shared<RuntimeDiagnosticHandoff>(1,deadline,clock);
  if(mode=="stable"){
    CHECK(h->failure()==Reason::none && !h->binding() && !h->quiescent());
    CHECK(h->execute(queue) && queue.id==1 && queue.deadline==deadline && !h->binding());
    queue.publish();auto b=h->binding();RuntimeDiagnosticSnapshot s;CHECK(b && b->snapshot(s) && s.deadline==deadline);
    h->cancel();CHECK(!h->binding() && !h->quiescent() && b->failure()==Reason::cancelled);
    queue.retire();CHECK(h->quiescent());
  }else if(mode=="invalid"){
    for(auto id:{std::uint64_t(0),UINT64_MAX}){RuntimeDiagnosticHandoff v(id,deadline,clock);CHECK(v.failure()==Reason::configuration && !v.execute(queue) && v.quiescent());}
    RuntimeDiagnosticHandoff long_wait(1,deadline+1ns,clock);CHECK(long_wait.failure()==Reason::configuration);
    RuntimeDiagnosticHandoff expired(1,clock.now(),clock);CHECK(expired.failure()==Reason::deadline);
    clock.ticks=std::chrono::duration_cast<std::chrono::nanoseconds>(Clock::time_point::max().time_since_epoch()).count();
    RuntimeDiagnosticHandoff maximum(1,Clock::time_point::max(),clock);CHECK(maximum.failure()==Reason::configuration && queue.calls==0);
  }else if(mode=="late"){
    clock.add(5s);CHECK(!h->execute(queue) && h->failure()==Reason::deadline && queue.calls==0 && h->quiescent());
  }else if(mode=="queue_cost"){
    clock.add(2s);CHECK(h->execute(queue) && queue.deadline==deadline);queue.publish();clock.add(3s);
    CHECK(h->failure()==Reason::deadline && !h->binding() && !h->quiescent());queue.retire();CHECK(h->quiescent());
  }else if(mode=="rollback"){
    clock.add(-1ns);CHECK(h->failure()==Reason::unavailable && !h->execute(queue) && queue.calls==0);
    clock.add(1ns);CHECK(h->failure()==Reason::unavailable);
  }else if(mode=="cancel_before"){
    h->cancel();CHECK(h->quiescent() && !h->execute(queue) && queue.calls==0 && h->failure()==Reason::cancelled);
  }else if(mode=="cancel_during"){
    queue.hook=[&]{h->cancel();CHECK(!h->quiescent());};
    CHECK(!h->execute(queue) && queue.ticket->state()==RuntimeDiagnosticTicket::State::stopped && !h->quiescent());
    queue.retire();CHECK(h->quiescent());
  }else if(mode=="cancel_after"){
    CHECK(h->execute(queue));h->cancel();CHECK(!queue.ticket->publish(snapshot(deadline)) && !h->quiescent());
    queue.retire();CHECK(h->quiescent());
  }else if(mode=="duplicate"){
    CHECK(h->execute(queue));queue.publish();CHECK(!h->execute(queue) && queue.calls==1 && h->binding());
    h->cancel();queue.retire();
  }else if(mode=="rejected"){
    queue.reject=true;CHECK(!h->execute(queue) && h->failure()==Reason::unavailable && h->quiescent());
  }else if(mode=="cause"){
    h->cancel(Reason::peer_lost);clock.add(5s);h->cancel(Reason::lifecycle);CHECK(h->failure()==Reason::peer_lost);
    RuntimeDiagnosticHandoff invalid(2,clock.now()+5s,clock);invalid.cancel(Reason::none);CHECK(invalid.failure()==Reason::protocol);
  }else if(mode=="lifecycle"){
    CHECK(h->execute(queue));queue.publish();queue.generation.advance();CHECK(h->failure()==Reason::lifecycle && !h->binding() && !h->quiescent());
    queue.retire();CHECK(h->quiescent());
  }else if(mode=="foreign_retire"){
    CHECK(h->execute(queue));queue.publish();h->cancel();
    std::thread foreign([&]{CHECK(!queue.ticket->retire() && !h->quiescent());});foreign.join();queue.retire();CHECK(h->quiescent());
  }else if(mode=="race"){
    for(unsigned i=0;i<100;++i){
      Queue q(clock);auto handoff=std::make_shared<RuntimeDiagnosticHandoff>(i+1,deadline,clock);std::atomic<bool> go{};
      std::thread other([&]{while(!go.load())std::this_thread::yield();handoff->cancel();});
      go=true;handoff->execute(q);other.join();CHECK(!handoff->binding() && handoff->failure()==Reason::cancelled);
      if(q.ticket){CHECK(q.ticket->state()==RuntimeDiagnosticTicket::State::stopped);q.retire();}CHECK(handoff->quiescent());
    }
  }else if(mode=="publication"){
    for(unsigned i=0;i<100;++i){Queue q(clock);auto handoff=std::make_shared<RuntimeDiagnosticHandoff>(i+1,deadline,clock);std::atomic<bool> done{};
      std::thread reader([&]{while(!done.load()){auto b=handoff->binding();if(b){RuntimeDiagnosticSnapshot s;CHECK(b->snapshot(s) && s.deadline==deadline);}}});
      CHECK(handoff->execute(q));q.publish();done=true;reader.join();handoff->cancel();q.retire();
    }
  }else if(mode=="retained_callback"){
    auto weak=std::weak_ptr(h);std::function<void()> callback=[h,&queue]{CHECK(!h->execute(queue));};
    h->cancel();h.reset();CHECK(!weak.expired());callback();callback={};CHECK(weak.expired() && queue.calls==0);
  }else if(mode=="late_copies"){
    auto weak=std::weak_ptr(h);h->cancel();
    auto copy=[h,&queue]{CHECK(!h->execute(queue) && !h->binding() && h->quiescent());};
    h.reset();CHECK(!weak.expired());
    std::thread one(copy),two(copy);one.join();two.join();
    CHECK(queue.calls==0 && !weak.expired());
    // The local closure remains an owner until the enclosing scope ends.
    {auto moved=std::move(copy);CHECK(!weak.expired());}
    CHECK(weak.expired());
  }else if(mode=="retired_copy"){
    CHECK(h->execute(queue));queue.publish();auto binding=h->binding();CHECK(binding);
    h->cancel();queue.retire();CHECK(h->quiescent());
    auto weak=std::weak_ptr(h);std::function<void()> copy=[h,&queue]{
      CHECK(!h->execute(queue) && !h->binding() && h->quiescent() && h->failure()==Reason::cancelled);
    };
    h.reset();copy();copy();CHECK(queue.calls==1 && binding->failure()==Reason::cancelled);
    copy={};CHECK(weak.expired());
  }else if(mode=="duplicate_inflight"){
    std::binary_semaphore entered(0),release(0);
    queue.hook=[&]{entered.release();release.acquire();};
    std::thread first([&]{CHECK(!h->execute(queue));queue.retire();});
    entered.acquire();
    std::thread duplicate([&]{CHECK(!h->execute(queue));});duplicate.join();
    h->cancel();CHECK(!h->quiescent());release.release();first.join();
    CHECK(queue.calls==1 && !h->binding() && h->quiescent() && h->failure()==Reason::cancelled);
  }else if(mode=="worker" || mode=="blocked" || mode=="close_failure"){
    CHECK(h->execute(queue));queue.publish();State child;child.close_ok=mode!="close_failure";
    std::binary_semaphore entered(0),go(0);
    if(mode=="blocked")child.sample_hook=[&](auto&){entered.release();go.acquire();};
    auto w=make_runtime_diagnostic_worker(expectation(),factory(child),h->binding());
    CHECK(w->submit_until(request(),snapshot(deadline).epochs,deadline));
    if(mode=="blocked")entered.acquire();
    else{Sink sink;eventually([&]{auto r=deliver_diagnostic(*w,sink);CHECK(r!=DiagnosticDeliveryResult::rejected);return r==DiagnosticDeliveryResult::complete;});CHECK(sink.bytes==diagnostic_response_size);}
    CHECK(!wait_runtime_diagnostic_stopped(*h,w.get(),Clock::now()+20ms) && !w->status().joined && !h->quiescent());
    queue.retire();CHECK(h->quiescent());
    if(mode=="blocked"){CHECK(!wait_runtime_diagnostic_stopped(*h,w.get(),Clock::now()+1ms) && !w->status().joined && child.closes==0);go.release();}
    CHECK(wait_runtime_diagnostic_stopped(*h,w.get(),Clock::now()+3s)==child.close_ok);
    CHECK(w->status().joined && w->status().cleanup_verified==child.close_ok && child.closes==1);
  }else if(mode=="no_worker"){
    CHECK(wait_runtime_diagnostic_stopped(*h,nullptr,Clock::now()) && h->quiescent());
  }else CHECK(false);
}
