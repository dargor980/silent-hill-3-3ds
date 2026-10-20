// Own doubles and oracles. Provider code is included only from private exact fragments.
#include "check.hpp"
#include "delivery_fixture.hpp"
#include "sh3_observer/runtime_diagnostic_ticket.hpp"
#include "sh3_observer/worker_drain.hpp"
#include "sh3_observer/external_waits.hpp"
#include "sh3_observer/physical_writes.hpp"
#include "sh3_observer/host_epoch.hpp"
#include <atomic>
#include <chrono>
#include <cstdio>
#include <functional>
#include <mutex>
#include <semaphore>
#include <string>
#include <thread>
#include <vector>
#include <limits>
#include <stdexcept>
#include "sh3_observer/runtime_diagnostic_handoff.hpp"
using namespace sh3::observer;
using namespace std::chrono_literals;
using u64=std::uint64_t;using Clock=PineDrain::Clock;using DrainState=PineDrain::State;
using Ticket=RuntimeDiagnosticTicket;using Reason=DiagnosticRejection;
#define pxAssert(x) CHECK(x)
enum class VMState {Paused,Running};
std::atomic<VMState> vm_state{VMState::Paused};
thread_local bool s_observer_cpu_thread=false;
thread_local CpuBoundary s_observer_cpu_boundary;
struct Config {
 struct {struct {bool EnableEE{},EnableIOP{},EnableVU0{},EnableVU1{},EnableEECache{},EnableFastmem{};} Recompiler;} Cpu;
 struct {bool vuThread{};} Speedhacks;
 bool EnablePINE=true;
} EmuConfig;
struct Cpu {} intCpu,psxInt,CpuIntVU0,CpuIntVU1,otherCpu;
Cpu *Cpu=&intCpu,*psxCpu=&psxInt,*CpuVU0=&CpuIntVU0,*CpuVU1=&CpuIntVU1;
bool s_cpu_implementation_changed=false,dump=false,ra=false;
constexpr bool newVifDynaRec=true;
namespace GSDumpReplayer {bool IsReplayingDump(){return dump;}}
namespace Achievements {bool IsUsingRAIntegration(){return ra;}}
CooperativeGate pine_gate;
HostEpoch s_observer_pine_generation;
namespace PINEServer {
 auto BeginObserverExclusion(Clock::time_point deadline){return pine_gate.close(deadline);}
 std::uint64_t GetObserverGeneration(){return s_observer_pine_generation.current();}
 bool IsInitialized(){return true;}
}
std::atomic<unsigned> wakes{},dispatches{};
namespace Host {
std::function<void()> pending_callback;bool dispatch_failure{};
void WakeObserverPineDrain(){++wakes;}
void RunOnCPUThread(std::function<void()> callback,bool block){
 CHECK(!block);if(dispatch_failure)throw std::runtime_error("synthetic dispatch failure");
 CHECK(!pending_callback);pending_callback=std::move(callback);
}
}
namespace VMManager {
 VMState GetState(){return vm_state.load();}
 namespace Internal {
#ifdef SH3_ENABLE_OBSERVER
#include "boundary_header.inc"
 bool IsObserverCpuThread();bool CanRequestObserverWorker();void BeforeObserverProducer();
 bool WaitObserverWorkerDrain();bool QueueObserverPineDrain(u64,std::chrono::milliseconds);bool CancelObserverPineDrain(u64);
 bool ObserverPineDrainPending();bool PollObserverPineDrain();PineDrain::Result GetObserverPineDrainResult();
 CpuBoundary::Activity EnterObserverCpuActivity();AdmissionProfile SampleObserverAdmissionProfile();
#endif
 }
}
#ifdef SH3_ENABLE_OBSERVER
struct Wake {void NotifyOfWork(){++wakes;}};
struct VU_Thread {
 ControlWakeup wake;WorkerControl m_observer_control{wake};WorkerControl::Token m_observer_owned{};
 std::uint32_t m_observer_generation{};std::atomic<bool> m_shutdown_flag{};std::atomic<int> m_ato_read_pos{};
 Wake semaEvent;
 int GetWritePos(){return 0;}
 bool RequestObserverControl(WorkerControl::Token);bool ReleaseObserverControl(WorkerControl::Token);
 void CancelObserverControl();WorkerControl::Lifecycle GetObserverLifecycle()const;
 WorkerControl::Status GetObserverStatus(WorkerControl::Token)const;
 bool StartObserverControl();void ServiceObserverControl();void StopObserverControl();
} vu1Thread;
namespace MTGS {
 std::atomic<bool> s_open_flag{true},s_shutdown_flag{},s_SignalRingEnable{},s_VsyncSignalListener{};
 std::atomic<unsigned> s_ReadPos{},s_WritePos{};Wake s_sem_event;
 bool IsOpen(){return s_open_flag.load();}
}
#include "sh3-observer/pcsx2/vu_control.inc"
#include "sh3-observer/pcsx2/gs_control.inc"
#include "owner.inc"
#include "stop.inc"
#include "boundary.inc"
#include "cpu_actor.inc"
#include "cpu_guard.inc"
#include "before.inc"
#include "wait.inc"
#include "queue.inc"
#include "cancel.inc"
#include "pending.inc"
#include "result.inc"
#include "poll.inc"
#include "activity.inc"
#include "sample.inc"
#include "sh3-observer/pcsx2/runtime_coordinator.inc"
#include "sh3-observer/pcsx2/runtime_frontend.inc"
std::atomic<bool> quit_vu{},quit_gs{},allow_vu{true},allow_gs{true};
std::atomic<RuntimeDiagnosticBinding*> watched{};
std::thread vu_actor,gs_actor;
std::mutex gs_mutex;
template<class F>void until(F ready){const auto end=Clock::now()+3s;while(!ready()){CHECK(Clock::now()<end);std::this_thread::sleep_for(100us);}}
void start_workers(){
 const auto revision=runtime_revocation().current();
 vu_actor=std::thread([]{CHECK(vu1Thread.StartObserverControl());while(!quit_vu.load()){
  if(allow_vu.load()){
   const auto token=vu1Thread.m_observer_control.pending(vu1Thread.m_observer_generation);
   vu1Thread.ServiceObserverControl();
   if(token.id && watched.load())CHECK(watched.load()->failure()!=Reason::none);
  }
  std::this_thread::sleep_for(100us);
 }vu1Thread.StopObserverControl();});
 gs_actor=std::thread([]{CHECK(MTGS::StartObserverControl());std::unique_lock lock(gs_mutex);while(!quit_gs.load()){
  if(allow_gs.load()){
   const auto token=MTGS::s_observer_control.pending(MTGS::s_observer_generation);
   MTGS::ServiceObserverControl(lock);
   if(token.id && watched.load())CHECK(watched.load()->failure()!=Reason::none);
  }
  std::this_thread::sleep_for(100us);
 }MTGS::StopObserverControl();});
 until([]{return vu1Thread.GetObserverLifecycle().online && MTGS::GetObserverLifecycle().online;});
 CHECK(runtime_revocation().current()==revision+2);
}
void close_workers(){
 StopObserverPineDrain();quit_vu=true;quit_gs=true;allow_vu=true;allow_gs=true;
 if(vu_actor.joinable())vu_actor.join();if(gs_actor.joinable())gs_actor.join();
 watched=nullptr;CHECK(!s_observer_pine_drain.active() && pine_gate.enter());
}
auto queue_runtime(u64 id=1,std::chrono::milliseconds timeout=2000ms){
 auto t=VMManager::Internal::QueueObserverRuntimeDiagnostic(id,timeout);CHECK(t && t->state()==Ticket::State::pending);return t;
}
void ready(const std::shared_ptr<Ticket>& t){
 until([&]{CHECK(VMManager::Internal::PollObserverPineDrain());CHECK(t->state()!=Ticket::State::stopped);return t->state()==Ticket::State::ready;});
 CHECK(s_observer_pine_drain.status().state==DrainState::held && !pine_gate.enter());
}
void released(const std::shared_ptr<Ticket>& t){
 CHECK(t->state()==Ticket::State::stopped && !t->binding());
 CHECK(!s_observer_pine_drain.active() && pine_gate.enter() && t->retired());
 CHECK(!vu1Thread.m_observer_owned.id && !MTGS::s_observer_owned.id);
}
void poll_stopped(const std::shared_ptr<Ticket>& t){CHECK(VMManager::Internal::PollObserverPineDrain());released(t);}
// Qt dependencies are controlled doubles; the dispatch branch is exact private code.
struct QEventLoop {void exec(){++dispatches;}void quit(){}};
struct QTimer {void setSingleShot(bool){}void start(unsigned){}void timeout(){}};
struct QObject {template<class...T>static void connect(T...) {}};
void pump(QEventLoop* m_event_loop,std::atomic<bool>& m_shutdown_flag){
 while(VMManager::Internal::ObserverPineDrainPending()){
  auto boundary=VMManager::Internal::EnterObserverCpuBoundary();CHECK(boundary.valid());
#include "dispatch.inc"
  CHECK(false);
 }
}
#endif
unsigned effects{};
void transition(unsigned index){switch(index){
case 0: {
#include "entry_set_state.inc"
#ifdef SH3_ENABLE_OBSERVER
CHECK(!s_observer_pine_drain.active());CHECK(pine_gate.enter());
#endif
++effects;break;}
case 1: {
#include "entry_initialize_cpu.inc"
#ifdef SH3_ENABLE_OBSERVER
CHECK(!s_observer_pine_drain.active());CHECK(pine_gate.enter());
#endif
++effects;break;}
case 2: {
#include "entry_shutdown_cpu.inc"
#ifdef SH3_ENABLE_OBSERVER
CHECK(!s_observer_pine_drain.active());CHECK(pine_gate.enter());
#endif
++effects;break;}
case 3: {
#include "entry_settings.inc"
#ifdef SH3_ENABLE_OBSERVER
CHECK(!s_observer_pine_drain.active());CHECK(pine_gate.enter());
#endif
++effects;break;}
case 4: {
#include "entry_core_settings.inc"
#ifdef SH3_ENABLE_OBSERVER
CHECK(!s_observer_pine_drain.active());CHECK(pine_gate.enter());
#endif
++effects;break;}
case 5: {
#include "entry_initialize_vm.inc"
#ifdef SH3_ENABLE_OBSERVER
CHECK(!s_observer_pine_drain.active());CHECK(pine_gate.enter());
#endif
++effects;break;}
case 6: {
#include "entry_shutdown_vm.inc"
#ifdef SH3_ENABLE_OBSERVER
CHECK(!s_observer_pine_drain.active());CHECK(pine_gate.enter());
#endif
++effects;break;}
case 7: {
#include "entry_reset_vm.inc"
#ifdef SH3_ENABLE_OBSERVER
CHECK(!s_observer_pine_drain.active());CHECK(pine_gate.enter());
#endif
++effects;break;}
case 8: {
#include "entry_load.inc"
#ifdef SH3_ENABLE_OBSERVER
CHECK(!s_observer_pine_drain.active());CHECK(pine_gate.enter());
#endif
++effects;break;}
case 9: {
#include "entry_save.inc"
#ifdef SH3_ENABLE_OBSERVER
CHECK(!s_observer_pine_drain.active());CHECK(pine_gate.enter());
#endif
++effects;break;}
case 10: {
#include "entry_load_public.inc"
#ifdef SH3_ENABLE_OBSERVER
CHECK(!s_observer_pine_drain.active());CHECK(pine_gate.enter());
#endif
++effects;break;}
case 11: {
#include "entry_load_slot.inc"
#ifdef SH3_ENABLE_OBSERVER
CHECK(!s_observer_pine_drain.active());CHECK(pine_gate.enter());
#endif
++effects;break;}
case 12: {
#include "entry_save_slot.inc"
#ifdef SH3_ENABLE_OBSERVER
CHECK(!s_observer_pine_drain.active());CHECK(pine_gate.enter());
#endif
++effects;break;}
case 13: {
#include "entry_caches.inc"
#ifdef SH3_ENABLE_OBSERVER
CHECK(!s_observer_pine_drain.active());CHECK(pine_gate.enter());
#endif
++effects;break;}
case 14: {
#include "entry_execute.inc"
#ifdef SH3_ENABLE_OBSERVER
CHECK(!s_observer_pine_drain.active());CHECK(pine_gate.enter());
#endif
++effects;break;}
default:CHECK(false);}}
void pine_initialize(){
#include "pine_initialize.inc"
++effects;
}
void pine_deinitialize(){
#include "pine_deinitialize.inc"
++effects;
}
int main(int argc,char** argv){
 CHECK(argc==2);const std::string name=argv[1];
#ifdef SH3_ENABLE_OBSERVER
 s_observer_cpu_thread=true;s_observer_cpu_boundary.set_online(true);start_workers();
 std::vector<std::shared_ptr<RuntimeDiagnosticBinding>> keep_alive;
 if(name.rfind("frontend_",0)==0){
  if(name=="frontend_cpu_rejected")CHECK(!sh3::observer::pcsx2::queue_runtime_diagnostic(Clock::now()+2s));
  else {
   std::shared_ptr<RuntimeDiagnosticHandoff> h;
   const auto deadline=Clock::now()+(name=="frontend_late"?50ms:name=="frontend_invalid"?-1ms:2000ms);
   Host::dispatch_failure=name=="frontend_dispatch_failure";
   std::thread enqueue([&]{h=sh3::observer::pcsx2::queue_runtime_diagnostic(deadline);});enqueue.join();CHECK(h);
   if(name=="frontend_invalid" || name=="frontend_dispatch_failure"){
    CHECK(!Host::pending_callback && h->quiescent());
    CHECK(h->failure()==(name=="frontend_invalid"?Reason::deadline:Reason::unavailable));
   }else if(name=="frontend_no_callback"){
    h->cancel();CHECK(h->quiescent());Host::pending_callback={};
   }else if(name=="frontend_cancel_before" || name=="frontend_late" || name=="frontend_rejected"){
    if(name=="frontend_cancel_before")h->cancel();
    if(name=="frontend_late")std::this_thread::sleep_for(60ms);
    if(name=="frontend_rejected")vm_state=VMState::Running;
    auto callback=std::move(Host::pending_callback);callback();vm_state=VMState::Paused;
    CHECK(h->quiescent() && !h->binding() && !s_observer_pine_drain.active());
    CHECK(h->failure()==(name=="frontend_late"?Reason::deadline:name=="frontend_rejected"?Reason::unavailable:Reason::cancelled));
   }else{
    CHECK(name=="frontend_roundtrip" || name=="frontend_blocked" || name=="frontend_duplicate");
    auto callback=std::move(Host::pending_callback);callback();if(name=="frontend_duplicate")callback();
    auto boundary=VMManager::Internal::EnterObserverCpuBoundary();std::atomic<bool> done{},allow_retire{};
    std::thread io([&]{
     std::shared_ptr<RuntimeDiagnosticBinding> b;until([&]{CHECK(h->failure()==Reason::none);b=h->binding();return bool(b);});
     RuntimeDiagnosticSnapshot value;CHECK(b->snapshot(value) && value.deadline==deadline);
     delivery_fixture::State child;std::binary_semaphore entered(0),go(0);
     if(name=="frontend_blocked")child.sample_hook=[&](auto&){entered.release();go.acquire();};
     auto worker=make_runtime_diagnostic_worker(delivery_fixture::expectation(),delivery_fixture::factory(child),b);
     CHECK(worker->submit_until(delivery_fixture::request(),value.epochs,deadline));
     if(name=="frontend_blocked")entered.acquire();
     else {
      struct Sink final:DiagnosticDeliverySink {unsigned bytes{};
       bool write(const std::uint8_t*,std::size_t n,std::size_t& out,DiagnosticClock::Clock::duration)noexcept override{out=std::min<std::size_t>(n,3);bytes+=out;return true;}
      } sink;
      until([&]{const auto r=deliver_diagnostic(*worker,sink);CHECK(r!=DiagnosticDeliveryResult::rejected);return r==DiagnosticDeliveryResult::complete;});
      CHECK(sink.bytes==diagnostic_response_size);
     }
     CHECK(!wait_runtime_diagnostic_stopped(*h,worker.get(),Clock::now()+10ms));
     CHECK(!h->quiescent() && !worker->status().joined);allow_retire=true;
     until([&]{return h->quiescent();});
     if(name=="frontend_blocked"){CHECK(child.closes==0);go.release();}
     CHECK(wait_runtime_diagnostic_stopped(*h,worker.get(),Clock::now()+2s));
     CHECK(worker->status().joined && child.closes==1);done=true;
    });
    until([&]{if(h->failure()==Reason::none || allow_retire.load())VMManager::Internal::PollObserverPineDrain();return done.load();});
    io.join();CHECK(h->quiescent() && !s_observer_pine_drain.active() && pine_gate.enter());
   }
  }
 }else if(name=="legacy"){
  auto boundary=VMManager::Internal::EnterObserverCpuBoundary();CHECK(VMManager::Internal::QueueObserverPineDrain(1,2s));
  until([]{VMManager::Internal::PollObserverPineDrain();return !VMManager::Internal::ObserverPineDrainPending();});
  CHECK(s_observer_pine_result.state==DrainState::completed && !s_observer_runtime.ticket);
 }else if(name=="validation"){
  for(auto id:{u64(0),UINT64_MAX})CHECK(!VMManager::Internal::QueueObserverRuntimeDiagnostic(id,2s));
  for(auto timeout:{0ms,5001ms})CHECK(!VMManager::Internal::QueueObserverRuntimeDiagnostic(1,timeout));
  vm_state=VMState::Running;CHECK(!VMManager::Internal::QueueObserverRuntimeDiagnostic(1,2s));vm_state=VMState::Paused;
  std::thread foreign([]{CHECK(!VMManager::Internal::QueueObserverRuntimeDiagnostic(1,2s));});foreign.join();
  auto t=queue_runtime();CHECK(!VMManager::Internal::QueueObserverRuntimeDiagnostic(2,2s));
  CHECK(!VMManager::Internal::CancelObserverPineDrain(999) && t->state()==Ticket::State::pending);
  t->cancel();poll_stopped(t);CHECK(!VMManager::Internal::QueueObserverRuntimeDiagnostic(1,2s));
 }else if(name=="retained" || name=="old_ticket"){
  auto boundary=VMManager::Internal::EnterObserverCpuBoundary();auto t=queue_runtime();ready(t);auto b=t->binding();
  RuntimeDiagnosticSnapshot v;CHECK(b->snapshot(v));CHECK(v.epochs.host==host_epoch() && v.epochs.pine==PINEServer::GetObserverGeneration());
  CHECK(v.epochs.vu==vu1Thread.GetObserverLifecycle().generation && v.epochs.gs==MTGS::GetObserverLifecycle().generation);
  const auto assessment=assess_profile(v.facts);
  CHECK(assessment.unknown==(admission_bit(AdmissionCondition::rdebug_excluded)|admission_bit(AdmissionCondition::other_writers_excluded)));
  CHECK(assessment.violated==admission_bit(AdmissionCondition::vif_dynarec_disabled));
  for(unsigned i=0;i<5;++i){CHECK(VMManager::Internal::PollObserverPineDrain());CHECK(t->state()==Ticket::State::ready && boundary.valid());}
  t->cancel();poll_stopped(t);
  if(name=="old_ticket"){
   auto next=queue_runtime(2);ready(next);RuntimeDiagnosticSnapshot n;CHECK(next->binding()->snapshot(n) && n.scope_id>v.scope_id);
   t->cancel();CHECK(next->state()==Ticket::State::ready);next->cancel();poll_stopped(next);
  }
 }else if(name=="boundary" || name=="nested" || name=="activity"){
  std::shared_ptr<Ticket> t;
  {auto boundary=VMManager::Internal::EnterObserverCpuBoundary();t=queue_runtime();ready(t);
   if(name=="nested"){auto inner=VMManager::Internal::EnterObserverCpuBoundary();CHECK(!inner.valid());released(t);}
   if(name=="activity"){auto active=VMManager::Internal::EnterObserverCpuActivity();released(t);CHECK(!boundary.valid());}
  }released(t);
 }else if(name=="producer" || name=="foreign_producer" || name=="foreign_lifecycle" || name=="pine_start" || name=="pine_stop"){
  auto boundary=VMManager::Internal::EnterObserverCpuBoundary();auto t=queue_runtime();ready(t);auto b=t->binding();keep_alive.push_back(b);watched=b.get();
  if(name=="producer")VMManager::Internal::BeforeObserverProducer();
  else if(name=="foreign_producer"){std::thread f([]{VMManager::Internal::BeforeObserverProducer();});f.join();}
  else if(name=="foreign_lifecycle"){std::thread f([]{before_lifecycle(LifetimeKind::remap,0);});f.join();}
  else if(name=="pine_start")pine_initialize();else pine_deinitialize();
  CHECK(b->failure()==Reason::lifecycle && t->state()==Ticket::State::stopped);
  if(name!="producer")poll_stopped(t);else released(t);
 }else if(name=="pending_pine" || name=="pending_vu" || name=="pending_gs"){
  auto boundary=VMManager::Internal::EnterObserverCpuBoundary();auto prior=name=="pending_pine"?pine_gate.enter():CooperativeGate::Work{};
  allow_vu=name!="pending_vu";allow_gs=name!="pending_gs";auto t=queue_runtime();
  for(unsigned i=0;i<5;++i){CHECK(VMManager::Internal::PollObserverPineDrain());CHECK(t->state()==Ticket::State::pending && !t->binding());std::this_thread::sleep_for(1ms);}
  t->cancel();poll_stopped(t);prior={};
 }else if(name=="deadline" || name=="external_wait"){
  auto boundary=VMManager::Internal::EnterObserverCpuBoundary();auto t=queue_runtime(1,name=="deadline"?50ms:2000ms);ready(t);auto b=t->binding();
  if(name=="deadline"){std::this_thread::sleep_for(60ms);CHECK(b->failure()==Reason::deadline);poll_stopped(t);}
  else {auto wait=s_observer_external_waits.wait(true);CHECK(wait.tracked());poll_stopped(t);CHECK(b->failure()==Reason::lifecycle);}
 }else if(name=="facts"){
  std::vector<bool*> options{&EmuConfig.Cpu.Recompiler.EnableEE,&EmuConfig.Cpu.Recompiler.EnableIOP,
   &EmuConfig.Cpu.Recompiler.EnableVU0,&EmuConfig.Cpu.Recompiler.EnableVU1,&EmuConfig.Cpu.Recompiler.EnableEECache,
   &EmuConfig.Cpu.Recompiler.EnableFastmem,&EmuConfig.Speedhacks.vuThread,&s_cpu_implementation_changed,&dump,&ra};
  u64 id=0;
  for(auto option:options){auto boundary=VMManager::Internal::EnterObserverCpuBoundary();auto t=queue_runtime(++id);ready(t);auto b=t->binding();
   *option=true;poll_stopped(t);*option=false;CHECK(b->failure()==Reason::lifecycle && !t->binding());}
 }else if(name=="entry_hooks"){
  for(unsigned i=0;i<15;++i){s_observer_cpu_thread=true;s_observer_cpu_boundary.set_online(true);
   auto boundary=VMManager::Internal::EnterObserverCpuBoundary();auto t=queue_runtime(i+1);ready(t);auto b=t->binding();
   transition(i);released(t);CHECK(b->failure()==Reason::lifecycle);}
  CHECK(effects==15);
 }else if(name=="stop_vu" || name=="stop_gs"){
  auto boundary=VMManager::Internal::EnterObserverCpuBoundary();auto t=queue_runtime();ready(t);auto b=t->binding();keep_alive.push_back(b);watched=b.get();
  // A worker exit announces revocation before its retained control can stop.
  if(name=="stop_vu"){std::thread signal([]{VMManager::Internal::BeforeObserverProducer();quit_vu=true;});signal.join();}
  else {std::thread signal([]{VMManager::Internal::BeforeObserverProducer();quit_gs=true;});signal.join();}
  CHECK(t->state()==Ticket::State::stopped);poll_stopped(t);
 }else if(name=="direct_release" || name=="direct_vu_release"){
  auto boundary=VMManager::Internal::EnterObserverCpuBoundary();auto t=queue_runtime();ready(t);auto b=t->binding();keep_alive.push_back(b);watched=b.get();
  if(name=="direct_release")CHECK(MTGS::ReleaseObserverControl(MTGS::s_observer_owned));
  else CHECK(vu1Thread.ReleaseObserverControl(vu1Thread.m_observer_owned));CHECK(b->failure()==Reason::lifecycle);poll_stopped(t);
 }else if(name=="worker_blocked"){
  auto boundary=VMManager::Internal::EnterObserverCpuBoundary();auto t=queue_runtime();ready(t);auto b=t->binding();RuntimeDiagnosticSnapshot v;CHECK(b->snapshot(v));
  delivery_fixture::State child;std::binary_semaphore entered(0),go(0);
  child.sample_hook=[&](auto&){entered.release();go.acquire();};
  auto w=make_runtime_diagnostic_worker(delivery_fixture::expectation(),delivery_fixture::factory(child),b);
  CHECK(w->submit_until(delivery_fixture::request(),v.epochs,v.deadline));entered.acquire();
  t->cancel();poll_stopped(t);CHECK(child.closes==0 && !w->status().cleanup_verified);
  go.release();delivery_fixture::stopped(*w,Reason::cancelled);CHECK(child.closes==1);
 }else if(name=="qt_hold" || name=="qt_shutdown"){
  auto t=queue_runtime();std::atomic<bool> shutdown{};QEventLoop loop;
  std::thread io([&]{until([&]{return t->state()!=Ticket::State::pending;});CHECK(t->state()==Ticket::State::ready);
   std::this_thread::sleep_for(60ms);CHECK(t->state()==Ticket::State::ready && dispatches==0);
   if(name=="qt_shutdown")shutdown=true;else t->cancel();});
  pump(&loop,shutdown);io.join();released(t);CHECK(dispatches==0);
 }else CHECK(false);
 close_workers();s_observer_cpu_thread=false;s_observer_cpu_boundary.set_online(false);
#else
 CHECK(name=="disabled");const auto before=runtime_revocation().current();
 for(unsigned i=0;i<15;++i)transition(i);pine_initialize();pine_deinitialize();
 CHECK(effects==17 && runtime_revocation().current()==before && host_epoch()==1);
#endif
 std::printf("{\"case\":\"%s\",\"result\":\"PASS\"}\n",name.c_str());
}
