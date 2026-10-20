#include "delivery_fixture.hpp"
#include "sh3_observer/runtime_diagnostic.hpp"
#include "sh3_observer/worker_drain.hpp"
#include <condition_variable>
#include <mutex>
#include <string>
#include <vector>
using namespace delivery_fixture;
namespace {
constexpr AdmissionCondition structural[]={AdmissionCondition::cpu_thread,AdmissionCondition::cpu_boundary,
 AdmissionCondition::paused,AdmissionCondition::pine_excluded,AdmissionCondition::gs_drained,AdmissionCondition::vu_drained};
bool required(std::size_t i){for(auto k:structural)if(static_cast<std::size_t>(k)==i)return true;return false;}
RuntimeDiagnosticSnapshot snapshot(Clock::time_point deadline){
 RuntimeDiagnosticSnapshot s;s.scope_id=42;s.deadline=deadline;s.epochs={1,2,3,4};
 for(auto key:structural)s.facts[static_cast<std::size_t>(key)]=AdmissionFact::satisfied;return s;
}
std::uint64_t u64(const DiagnosticBytes& bytes,std::size_t pos){std::uint64_t n=0;for(unsigned i=0;i<8;++i)n|=std::uint64_t(bytes[pos+i])<<(8*i);return n;}
struct ProbeState:State {
 std::function<void()> create_hook;Reason prepare_result{},sample_result{};unsigned contaminated{};bool empty{};
 std::thread::id factory_thread,prepare_thread,sample_thread,close_thread,destroy_thread;
};
struct ProbeWork final:DiagnosticWork {
 ProbeState& s;Work inner;explicit ProbeWork(ProbeState& state):s(state),inner(state){}
 ~ProbeWork(){s.destroy_thread=std::this_thread::get_id();}
 Reason prepare(DiagnosticBudget& b)override{s.prepare_thread=std::this_thread::get_id();inner.prepare(b);return s.prepare_result;}
 Reason sample(DiagnosticBudget& b,DiagnosticObservation& out)override{
  s.sample_thread=std::this_thread::get_id();inner.sample(b,out);
  if(s.contaminated==1)out.epochs={1,2,3,4};if(s.contaminated==2)out.facts[0]=AdmissionFact::satisfied;
  return s.sample_result;
 }
 bool close()noexcept override{s.close_thread=std::this_thread::get_id();return inner.close();}
};
struct ProbeFactory final:DiagnosticWorkFactory {
 ProbeState& s;explicit ProbeFactory(ProbeState& state):s(state){}
 std::unique_ptr<DiagnosticWork> create(DiagnosticBudget&)override{
  ++s.creates;s.factory_thread=std::this_thread::get_id();if(s.create_hook)s.create_hook();
  if(s.empty)return {};return std::make_unique<ProbeWork>(s);
 }
};
std::unique_ptr<DiagnosticWorkFactory> probe(ProbeState& s){return std::make_unique<ProbeFactory>(s);}
struct Sink final:DiagnosticDeliverySink {
 std::shared_ptr<RuntimeDiagnosticBinding> binding;std::size_t bytes{};bool late{};
 bool write(const std::uint8_t*,std::size_t n,std::size_t& wrote,Clock::duration)noexcept override{
  wrote=late?n:std::min(n,std::size_t{17});bytes+=wrote;binding->revoke();return true;
 }
};
void drive_rejected(DiagnosticWorker& w){DiagnosticCompletion c;eventually([&]{CHECK(!w.take_for_delivery(c));return w.status().reason!=Reason::none;});CHECK(c.bytes==DiagnosticBytes{});}
}
int main(int argc,char** argv){
 CHECK(argc==2);const std::string mode=argv[1];FakeClock clock;ProbeState s;
 auto binding=std::make_shared<RuntimeDiagnosticBinding>(clock);auto state=snapshot(clock.now()+5s);
 if(mode=="snapshot"){
  RuntimeDiagnosticSnapshot out;CHECK(binding->failure()==Reason::unavailable && !binding->snapshot(out));CHECK(out.scope_id==0);
  CHECK(binding->activate(state) && binding->revalidate(state) && binding->snapshot(out));CHECK(out.scope_id==42 && out.epochs.gs==4);
  state.facts[0]=AdmissionFact::violated;CHECK(binding->snapshot(out) && out.facts[0]==AdmissionFact::satisfied);
  binding->revoke();CHECK(!binding->snapshot(out) && out.scope_id==0 && out.facts==AdmissionProfile{});
 }else if(mode=="structural"){
  for(auto key:structural)for(auto fact:{AdmissionFact::unknown,AdmissionFact::violated,static_cast<AdmissionFact>(255)}){
   RuntimeDiagnosticBinding b(clock);auto value=state;value.facts[static_cast<std::size_t>(key)]=fact;
   CHECK(!b.activate(value) && b.failure()==Reason::lifecycle);CHECK(!b.activate(state));
  }
 }else if(mode=="facts"){
  for(std::size_t i=0;i<admission_condition_count;++i)if(!required(i))
   for(auto fact:{AdmissionFact::unknown,AdmissionFact::violated,AdmissionFact::satisfied,static_cast<AdmissionFact>(255)}){
    auto b=std::make_shared<RuntimeDiagnosticBinding>(clock);auto value=state;value.facts[i]=fact;CHECK(b->activate(value));
    ProbeState child;auto w=make_runtime_diagnostic_worker(expectation(),probe(child),b);
    CHECK(w->submit_until(request(),value.epochs,value.deadline));const auto result=take(*w);
    const auto normalized=fact==static_cast<AdmissionFact>(255)?AdmissionFact::unknown:fact;
    CHECK(result.bytes[244+i]==static_cast<std::uint8_t>(normalized));
    const auto bit=std::uint32_t{1}<<i;CHECK(bool(result.gates.unknown&bit)==(normalized==AdmissionFact::unknown));CHECK(bool(result.gates.violated&bit)==(normalized==AdmissionFact::violated));
    CHECK(w->complete_delivery());w->cancel();stopped(*w,Reason::cancelled);
   }
 }else if(mode=="invalid_identity"){
  for(unsigned field=0;field<5;++field)for(auto value:{std::uint64_t{0},UINT64_MAX}){
   RuntimeDiagnosticBinding b(clock);auto n=state;
   switch(field){case 0:n.scope_id=value;break;case 1:n.epochs.host=value;break;case 2:n.epochs.pine=value;break;case 3:n.epochs.vu=value;break;case 4:n.epochs.gs=value;break;}
   CHECK(!b.activate(n) && b.failure()==Reason::lifecycle);
  }
 }else if(mode=="deadlines"){
  for(auto delta:{-1ns,0ns,1ns,5s+0ns,5s+1ns}){
   RuntimeDiagnosticBinding b(clock);auto value=state;value.deadline=clock.now()+delta;
   CHECK(b.activate(value)==(delta>0ns && delta<=5s));
   if(delta>5s)CHECK(b.failure()==Reason::configuration);
   else if(delta<=0ns)CHECK(b.failure()==Reason::deadline);
   else{clock.add(delta);CHECK(b.failure()==Reason::deadline);}
  }
  clock.ticks=Clock::time_point::max().time_since_epoch().count()-1;RuntimeDiagnosticBinding b(clock);state.deadline=Clock::time_point::max();CHECK(!b.activate(state) && b.failure()==Reason::configuration);
 }else if(mode=="owner"){
  for(bool activate:{false,true}){
   auto b=std::make_shared<RuntimeDiagnosticBinding>(clock);if(!activate)CHECK(b->activate(state));bool ok=true;
   std::thread foreign([&]{ok=activate?b->activate(state):b->revalidate(state);});foreign.join();CHECK(!ok && b->failure()==Reason::lifecycle);CHECK(!b->activate(state));
  }
 }else if(mode=="single_use"){
  CHECK(binding->activate(state));CHECK(!binding->activate(state) && binding->failure()==Reason::protocol);
  RuntimeDiagnosticBinding b(clock);b.revoke(Reason::peer_lost);CHECK(!b.activate(state) && b.failure()==Reason::peer_lost);
 }else if(mode=="changes"){
  for(unsigned field=0;field<25;++field){
   RuntimeDiagnosticBinding b(clock);CHECK(b.activate(state));auto value=state;
   if(field==0)++value.scope_id;else if(field==1)value.deadline-=1ns;else if(field==2)++value.epochs.host;else if(field==3)++value.epochs.pine;else if(field==4)++value.epochs.vu;else if(field==5)++value.epochs.gs;
   else if(field==24)value.epochs={};else value.facts[field-6]=required(field-6)?AdmissionFact::violated:AdmissionFact::satisfied;
   CHECK(!b.revalidate(value));CHECK(!b.revalidate(state) && b.failure()==Reason::lifecycle);
  }
 }else if(mode=="reason"){
  CHECK(binding->activate(state));binding->revoke(Reason::peer_lost);binding->revoke();clock.add(6s);CHECK(binding->failure()==Reason::peer_lost);
  for(auto reason:{Reason::none,static_cast<Reason>(255)}){RuntimeDiagnosticBinding b(clock);b.revoke(reason);CHECK(b.failure()==Reason::protocol);}
 }else if(mode=="clock"){
  CHECK(binding->activate(state));clock.add(-1ns);CHECK(binding->failure()==Reason::unavailable);
 }else if(mode=="worker"){
  CHECK(binding->activate(state));auto w=make_runtime_diagnostic_worker(expectation(),probe(s),binding);
  for(unsigned n=1;n<=3;++n){CHECK(binding->revalidate(state));CHECK(w->submit_until(request(n),state.epochs,state.deadline));auto c=take(*w);
   CHECK(u64(c.bytes,262)==1 && u64(c.bytes,270)==2 && u64(c.bytes,278)==3 && u64(c.bytes,286)==4);CHECK(w->complete_delivery());}
  w->cancel();stopped(*w,Reason::cancelled);CHECK(s.samples==3 && s.prepares==1 && s.closes==1);
  CHECK(s.factory_thread!=std::this_thread::get_id() && s.factory_thread==s.prepare_thread && s.factory_thread==s.sample_thread && s.factory_thread==s.close_thread && s.factory_thread==s.destroy_thread);
 }else if(mode=="unbound"){
  auto w=make_runtime_diagnostic_worker(expectation(),probe(s),binding);CHECK(!w->submit_until(request(),state.epochs,state.deadline));stopped(*w,Reason::unavailable);CHECK(s.creates==0);
  CHECK(!make_runtime_diagnostic_worker(expectation(),probe(s),{}));CHECK(!make_runtime_diagnostic_worker(expectation(),{},binding));
 }else if(mode=="revoke_factory"||mode=="revoke_prepare"||mode=="revoke_sample"){
  CHECK(binding->activate(state));
  if(mode=="revoke_factory")s.create_hook=[&]{binding->revoke();};
  if(mode=="revoke_prepare")s.prepare_hook=[&](auto&){binding->revoke();};
  if(mode=="revoke_sample")s.sample_hook=[&](auto&){binding->revoke();};
  auto w=make_runtime_diagnostic_worker(expectation(),probe(s),binding);CHECK(w->submit_until(request(),state.epochs,state.deadline));drive_rejected(*w);stopped(*w,Reason::lifecycle);CHECK(s.closes==1);
 }else if(mode=="revoke_ready"){
  CHECK(binding->activate(state));auto w=make_runtime_diagnostic_worker(expectation(),probe(s),binding);CHECK(w->submit_until(request(),state.epochs,state.deadline));
  eventually([&]{return w->status().phase==Phase::ready;});binding->revoke();DiagnosticCompletion c;CHECK(!w->take_for_delivery(c));stopped(*w,Reason::lifecycle);
 }else if(mode=="revoke_delivery"){
  for(bool last:{false,true}){
   ProbeState child;auto b=std::make_shared<RuntimeDiagnosticBinding>(clock);CHECK(b->activate(state));auto w=make_runtime_diagnostic_worker(expectation(),probe(child),b);
   CHECK(w->submit_until(request(),state.epochs,state.deadline));Sink sink;sink.binding=b;sink.late=last;DiagnosticDeliveryResult r;
   eventually([&]{r=deliver_diagnostic(*w,sink);return r!=DiagnosticDeliveryResult::waiting;});CHECK(r==DiagnosticDeliveryResult::rejected && sink.bytes==(last?294u:17u));stopped(*w,Reason::lifecycle);
  }
 }else if(mode=="scope_deadline"){
  state.deadline=clock.now()+3s;CHECK(binding->activate(state));auto w=make_runtime_diagnostic_worker(expectation(),probe(s),binding);
  CHECK(w->submit_until(request(),state.epochs,clock.now()+5s));take(*w);CHECK(w->complete_delivery());clock.add(2s);
  CHECK(w->submit_until(request(2),state.epochs,clock.now()+2s));take(*w);clock.add(1s);CHECK(!w->complete_delivery());stopped(*w,Reason::deadline);
 }else if(mode=="child_failures"){
  for(unsigned which=0;which<7;++which){
   ProbeState child;auto b=std::make_shared<RuntimeDiagnosticBinding>(clock);CHECK(b->activate(state));
   if(which==0)child.empty=true;if(which==1)child.prepare_result=Reason::inventory;if(which==2)child.sample_result=Reason::inventory;
   if(which==3||which==4)child.contaminated=which-2;
   if(which==5)child.prepare_hook=[](auto&){throw 1;};if(which==6)child.sample_hook=[](auto&){throw 1;};
   auto w=make_runtime_diagnostic_worker(expectation(),probe(child),b);CHECK(w->submit_until(request(),state.epochs,state.deadline));drive_rejected(*w);
   stopped(*w,which==1||which==2?Reason::inventory:which==3||which==4?Reason::protocol:Reason::unavailable);CHECK(child.closes==(which==0?0u:1u));
  }
 }else if(mode=="closure"){
  std::atomic<bool> entered{},release{};s.sample_hook=[&](auto&){entered=true;eventually([&]{return release.load();});};s.close_ok=false;
  CHECK(binding->activate(state));auto w=make_runtime_diagnostic_worker(expectation(),probe(s),binding);CHECK(w->submit_until(request(),state.epochs,state.deadline));eventually([&]{return entered.load();});
  binding->revoke();CHECK(w->status().reason==Reason::lifecycle);CHECK(!w->wait_stopped_until(Clock::now()+1ms) && !w->status().joined && s.closes==0);
  release=true;stopped(*w,Reason::lifecycle,false);CHECK(s.closes==1);
 }else if(mode=="shared_lifetime"){
  CHECK(binding->activate(state));std::weak_ptr<RuntimeDiagnosticBinding> weak=binding;auto w=make_runtime_diagnostic_worker(expectation(),probe(s),binding);binding.reset();CHECK(!weak.expired());
  CHECK(w->submit_until(request(),state.epochs,state.deadline));take(*w);weak.lock()->revoke();CHECK(!w->complete_delivery());stopped(*w,Reason::lifecycle);w.reset();CHECK(weak.expired());
 }else if(mode=="race"){
  for(unsigned i=0;i<100;++i){
   ProbeState child;auto b=std::make_shared<RuntimeDiagnosticBinding>(clock);CHECK(b->activate(state));auto w=make_runtime_diagnostic_worker(expectation(),probe(child),b);
   CHECK(w->submit_until(request(),state.epochs,state.deadline));take(*w);
   std::thread revoke([&]{b->revoke();});w->complete_delivery();revoke.join();CHECK(w->status().reason==Reason::lifecycle);stopped(*w,Reason::lifecycle);
  }
 }else if(mode=="publication_race"){
  for(unsigned i=0;i<100;++i){
   auto b=std::make_shared<RuntimeDiagnosticBinding>(clock);std::atomic<bool> done{};
   std::thread reader([&]{while(!done.load()){RuntimeDiagnosticSnapshot v;if(b->snapshot(v))CHECK(v.scope_id==state.scope_id && v.epochs.gs==4 && v.facts==state.facts);}});
   CHECK(b->activate(state));b->revoke();done=true;reader.join();RuntimeDiagnosticSnapshot v;CHECK(!b->snapshot(v));
  }
 }else if(mode=="invalid_validity"){
  struct Bad final:DiagnosticValidity {Reason failure()const noexcept override{return static_cast<Reason>(255);}};
  DiagnosticWorker w(expectation(),probe(s),clock,std::make_shared<Bad>());CHECK(!w.submit(request(),{}));stopped(w,Reason::protocol);
 }else if(mode=="autonomous"){
  struct ObservedClock final:DiagnosticClock {
   const std::thread::id owner=std::this_thread::get_id();std::atomic<unsigned> worker_reads{};
   Clock::time_point now()noexcept override{if(std::this_thread::get_id()!=owner)++worker_reads;return Clock::now();}
  };
  for(unsigned phase=0;phase<4;++phase){
   ObservedClock real_clock;ProbeState child;auto b=std::make_shared<RuntimeDiagnosticBinding>(real_clock);auto value=snapshot(Clock::now()+(phase==3?200ms:5000ms));CHECK(b->activate(value));
   auto w=make_runtime_diagnostic_worker(expectation(),probe(child),b);CHECK(w->submit_until(request(),value.epochs,Clock::now()+5s));
   if(phase==0||phase==3)eventually([&]{return w->status().phase==Phase::ready;});
   else{take(*w);if(phase==2)CHECK(w->complete_delivery());}
   if(phase!=3){
    // Observe repeated worker checks, not merely the phase set by the IO owner.
    // Six calls exceed the checks during the transition into the idle wait.
    const auto target=real_clock.worker_reads.load()+6;const auto limit=Clock::now()+1s;
    while(real_clock.worker_reads.load()<target && Clock::now()<limit)std::this_thread::sleep_for(100us);
    CHECK(real_clock.worker_reads.load()>=target);b->revoke();
   }
   // No status, budget, take or completion after revocation/deadline. DW wakes itself.
   CHECK(w->wait_stopped_until(Clock::now()+2s));stopped(*w,phase==3?Reason::deadline:Reason::lifecycle);CHECK(child.closes==1);
  }
 }else if(mode=="coordinator"){
  struct Barrier final:BarrierSource {CooperativeGate gate;CooperativeGate::Closure close(Clock::time_point d)noexcept override{return gate.close(d);}} barrier;
  CpuBoundary cpu;cpu.set_online(true);auto boundary=cpu.enter();CHECK(boundary.valid());
  auto b=std::make_shared<RuntimeDiagnosticBinding>();std::vector<unsigned> releases;
  struct Port final:WorkerPort {
   ControlWakeup wake;WorkerControl control{wake};unsigned id;std::shared_ptr<RuntimeDiagnosticBinding> binding;std::vector<unsigned>& releases;
   Port(unsigned n,std::shared_ptr<RuntimeDiagnosticBinding> b,std::vector<unsigned>& r):id(n),binding(std::move(b)),releases(r){}
   WorkerControl::Lifecycle lifecycle()const noexcept override{return control.lifecycle();}
   bool request(Token t)noexcept override{return control.request(t);}
   WorkerControl::Status status(Token t)const noexcept override{return control.status(t);}
   void release(Token t)noexcept override{CHECK(binding->failure()!=Reason::none);releases.push_back(id);CHECK(control.release(t));}
  }vu(1,b,releases),gs(2,b,releases);
  CHECK(vu.control.start(3) && gs.control.start(4));std::atomic<bool> quit{};
  auto actor=[&](Port& p,unsigned generation){while(!quit.load()){auto t=p.control.pending(generation);if(t.id)CHECK(p.control.acknowledge(t));std::this_thread::yield();}CHECK(p.control.stop(generation)==WorkerControl::StopResult::stopped);};
  std::thread vt(actor,std::ref(vu),3),gt(actor,std::ref(gs),4);
  WorkerDrain effects(vu,gs);RetainedDrain retained(cpu,barrier,effects);const auto deadline=Clock::now()+5s;
  CHECK(retained.submit({42,{1,2},deadline}));eventually([&]{return retained.step(true,{1,2})==PineDrain::State::held;});CHECK(!barrier.gate.enter());
  auto value=snapshot(deadline);CHECK(b->activate(value));std::atomic<bool> entered{},release{};
  s.sample_hook=[&](auto&){entered=true;eventually([&]{return release.load();});};auto w=make_runtime_diagnostic_worker(expectation(),probe(s),b);
  CHECK(w->submit_until(request(),value.epochs,deadline));eventually([&]{return entered.load();});
  b->revoke();CHECK(retained.cancel(42));CHECK(retained.retire().id==42);CHECK(releases==std::vector<unsigned>({2,1}));CHECK(bool(barrier.gate.enter()));
  // CPU has already retired guards before the non-CPU lifecycle owner joins DW.
  release=true;CHECK(w->status().reason==Reason::lifecycle);stopped(*w,Reason::lifecycle);quit=true;vt.join();gt.join();
 }else CHECK(false);
}
