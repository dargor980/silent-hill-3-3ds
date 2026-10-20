#include "delivery_fixture.hpp"
#include "sh3_observer/runtime_diagnostic_ticket.hpp"
#include "sh3_observer/physical_writes.hpp"
#include <cstdlib>
#include <new>
#include <string>
using namespace delivery_fixture;
namespace {
std::atomic<int> allocation_failure{-1};
RuntimeDiagnosticSnapshot snapshot(Clock::time_point deadline) {
  RuntimeDiagnosticSnapshot value; value.scope_id=7; value.deadline=deadline; value.epochs={1,2,3,4};
  for(auto c:{AdmissionCondition::cpu_thread,AdmissionCondition::cpu_boundary,AdmissionCondition::paused,
      AdmissionCondition::pine_excluded,AdmissionCondition::vu_drained,AdmissionCondition::gs_drained})
    value.facts[static_cast<std::size_t>(c)]=AdmissionFact::satisfied;
  return value;
}
}
void* operator new(std::size_t size) {
  auto n=allocation_failure.load();
  if(n>=0 && allocation_failure.fetch_sub(1)==0) throw std::bad_alloc();
  if(auto p=std::malloc(size ? size : 1)) return p;
  throw std::bad_alloc();
}
void operator delete(void* p) noexcept {std::free(p);}
void operator delete(void* p,std::size_t) noexcept {std::free(p);}
int main(int argc,char** argv) {
  CHECK(argc==2);const std::string mode=argv[1];RuntimeRevocation generation;FakeClock clock;
  auto t=make_runtime_diagnostic_ticket(generation,clock);CHECK(t);
  const auto value=snapshot(clock.now()+5s);using S=RuntimeDiagnosticTicket::State;
  if(mode=="generation") {
    CHECK(generation.current()==1 && generation.advance()==2);
    RuntimeRevocation end(UINT64_MAX-1);CHECK(end.advance()==UINT64_MAX && end.advance()==0 && end.advance()==0);
    RuntimeDiagnosticBinding dead(clock,&end);CHECK(!dead.activate(value) && dead.failure()==Reason::lifecycle);
    RuntimeRevocation maximum(UINT64_MAX);RuntimeDiagnosticBinding max(clock,&maximum);CHECK(!max.activate(value));
  } else if(mode=="pending") {
    CHECK(t->state()==S::pending && !t->binding());generation.advance();
    CHECK(t->state()==S::stopped && !t->publish(value) && !t->binding());
  } else if(mode=="ready") {
    CHECK(t->publish(value) && t->state()==S::ready && t->revalidate(value));auto b=t->binding();CHECK(b);
    generation.advance();CHECK(t->state()==S::stopped && !t->binding() && b->failure()==Reason::lifecycle);
    generation.advance();CHECK(!t->publish(value) && !t->revalidate(value));
  } else if(mode=="cancel") {
    for(bool active:{false,true}) {
      auto q=make_runtime_diagnostic_ticket(generation,clock);if(active)CHECK(q->publish(value));
      auto b=q->binding();q->cancel();CHECK(q->state()==S::stopped && !q->binding() && !q->publish(value));
      q->cancel(Reason::deadline);if(b)CHECK(b->failure()==Reason::cancelled);
    }
  } else if(mode=="old_ticket") {
    CHECK(t->publish(value));auto old=t->binding();t->cancel();
    auto next=make_runtime_diagnostic_ticket(generation,clock);CHECK(next->publish(value));
    t->cancel(Reason::lifecycle);CHECK(next->state()==S::ready && old->failure()==Reason::cancelled);
    CHECK(!next->publish(value) && next->state()==S::stopped);
  } else if(mode=="owner") {
    std::thread foreign([&]{CHECK(!t->publish(value));});foreign.join();CHECK(t->state()==S::stopped);
    t=make_runtime_diagnostic_ticket(generation,clock);CHECK(t->publish(value));
    std::thread foreign2([&]{CHECK(!t->revalidate(value));});foreign2.join();CHECK(t->state()==S::stopped);
  } else if(mode=="publication_race") {
    for(unsigned i=0;i<100;++i) {
      auto q=make_runtime_diagnostic_ticket(generation,clock);std::atomic<bool> go{};
      std::thread other([&]{while(!go.load())std::this_thread::yield();q->cancel();});
      go=true;q->publish(value);other.join();CHECK(q->state()==S::stopped && !q->binding());
    }
  } else if(mode=="worker") {
    CHECK(t->publish(value));State child;auto w=make_runtime_diagnostic_worker(expectation(),factory(child),t->binding());
    CHECK(w->submit_until(request(),value.epochs,clock.now()+5s));take(*w);
    std::thread foreign([&]{generation.advance();});foreign.join();
    CHECK(!w->complete_delivery());stopped(*w,Reason::lifecycle);CHECK(child.closes==1);
  } else if(mode=="deadline") {
    CHECK(t->publish(value));auto b=t->binding();clock.add(5s);
    CHECK(t->state()==S::stopped && b->failure()==Reason::deadline && !t->binding());
  } else if(mode=="lifecycle") {
    for(auto kind:{LifetimeKind::reset,LifetimeKind::restore,LifetimeKind::remap,LifetimeKind::settings,
        LifetimeKind::lost,LifetimeKind::shutdown,LifetimeKind::write}) {
      auto q=make_runtime_diagnostic_ticket(runtime_revocation(),clock);CHECK(q->publish(value));auto b=q->binding();
      const auto previous=host_epoch();before_lifecycle(kind,123);
      CHECK(host_epoch()==previous+1 && q->state()==S::stopped && b->failure()==Reason::lifecycle);
    }
  } else if(mode=="factory_failure") {
    for(int index:{0,1}) {allocation_failure=index;auto q=make_runtime_diagnostic_ticket(generation,clock);allocation_failure=-1;CHECK(!q);}
    CHECK(make_runtime_diagnostic_ticket(generation,clock));
  } else if(mode=="legacy") {
    RuntimeDiagnosticBinding b(clock);CHECK(b.activate(value));generation.advance();runtime_revocation().advance();
    CHECK(b.failure()==Reason::none && b.revalidate(value));
  } else CHECK(false);
}
