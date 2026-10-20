// Own orchestration and doubles. Provider bodies live only in private *.inc files.
#include "check.hpp"
#include "sh3_observer/retained_drain.hpp"
#include <QCoreApplication>
#include <QEventLoop>
#include <QThread>
#include <QTimer>
#include <mutex>
#include <algorithm>
#include <array>
#include <atomic>
#include <cstring>
#include <functional>
#include <iomanip>
#include <iostream>
#include <memory>
#include <thread>
#include <vector>
using u8 = std::uint8_t;
using u32 = std::uint32_t;
using uptr = std::uintptr_t;
struct u128 { u32 words[4]; };
using namespace sh3::observer;
using State = PineDrain::State;
using Clock = PineDrain::Clock;
using Progress = EffectDrainPort::Progress;
struct Source final : BarrierSource {
  CooperativeGate gate;
  CooperativeGate::Closure close(Clock::time_point d) noexcept override { return gate.close(d); }
} source;
CpuBoundary cpu;
auto& s_observer_cpu_boundary = cpu;
std::function<void()> at_release;
struct Port final : EffectDrainPort {
  Progress progress{Progress::pending};
  unsigned releases{};
  void begin(PineDrain::Request) noexcept override {}
  Progress poll(std::uint64_t) noexcept override { return progress; }
  void release(std::uint64_t) noexcept override {
    CHECK(!source.gate.enter());
    ++releases;
    if (at_release) at_release();
  }
} port;
RetainedDrain s_observer_pine_drain{cpu, source, port};
PineDrain::Result s_observer_pine_result;
static thread_local bool s_observer_cpu_thread = false;
namespace VMManager::Internal {
void BeforeObserverProducer();
CpuBoundary::Activity EnterObserverCpuActivity();
}
#ifdef SH3_ENABLE_OBSERVER
#include "stop.inc"
#include "before.inc"
#include "activity.inc"
#endif
unsigned effects{}, phase{}, cases{};
std::uint64_t digest = 1469598103934665603ULL, next_id{};
void hash(u32 value) { for (unsigned i=0;i<4;++i) {digest^=(value>>(i*8))&255;digest*=1099511628211ULL;} }
void effect(u32 kind) {
#ifdef SH3_ENABLE_OBSERVER
  if (phase>=2) {CHECK(!s_observer_pine_drain.active());CHECK(port.releases==1);CHECK(source.gate.enter());}
#endif
  ++effects;hash(kind);
}
CooperativeGate::Work prior;
void start(unsigned p) {
  CHECK(!s_observer_pine_drain.active());CHECK(source.gate.enter());
  phase=p;effects=0;port.releases=0;at_release=[&]{CHECK(effects==0);};
  port.progress=p==3?Progress::held:p==4?Progress::rejected:Progress::pending;
  if(!p)return;
  if(p==1)prior=source.gate.enter();
  CHECK(s_observer_pine_drain.submit({++next_id,{1,1},Clock::now()+std::chrono::seconds(5)}));
  auto b=cpu.enter();CHECK(s_observer_pine_drain.step(true,{1,1})==(p==3?State::held:p==4?State::rejected:State::draining));
}
void finish() {
#ifdef SH3_ENABLE_OBSERVER
  if(phase>=2) {CHECK(port.releases==1);CHECK(!s_observer_pine_drain.active());
    CHECK(s_observer_pine_result.state==(phase==4?State::rejected:State::cancelled));}
  if(phase==1) {CHECK(s_observer_pine_drain.active());CHECK(port.releases==0);CHECK(!source.gate.enter());}
#endif
  at_release={};prior={};
  if(s_observer_pine_drain.active()) {s_observer_pine_drain.cancel(next_id);s_observer_pine_drain.retire();}
  CHECK(source.gate.enter());++cases;
}
enum class VMState {Running,Paused,Stopping,Shutdown};
VMState vm_state=VMState::Paused;
namespace VMManager {
bool HasValidVM() {return vm_state!=VMState::Shutdown;}
VMState GetState() {return vm_state;}
void SetState(VMState s) {effect(1);vm_state=s;}
void SetPaused(bool p) {effect(2);vm_state=p?VMState::Paused:VMState::Running;}
void UpdateTargetSpeed() {effect(3);}
void IdlePollUpdate() {effect(4);}
}
namespace MTGS {
bool open=true;
bool IsOpen() {return open;}
void UpdateDisplayWindow() {effect(5);}
void WaitGS() {effect(6);}
}
namespace InputManager {
unsigned MakeHostKeyboardKey(unsigned n) {return n;}
void ClearBindStateFromSource(unsigned n) {CHECK(n==0);effect(7);}
}
namespace FullscreenUI {bool IsInitialized() {return true;}}
struct SettingsInterface {bool GetBoolValue(const char*,const char*,bool) {effect(8);return true;}};
std::atomic_int s_vm_locked_with_dialog{};
// QObject substitute for the full EmuThread. Its bodies below are exact;
// affinity and queued delivery use real QtCore, VM/GS/input are doubles.
class EmuThread : public QObject {
  Q_OBJECT
public:
  QEventLoop loop;
  QEventLoop* m_event_loop=&loop;
  QTimer timer;
  QTimer* m_background_controller_polling_timer=&timer;
  bool m_is_fullscreen{},m_is_rendering_to_main{},m_is_surfaceless{};
  bool m_save_state_on_shutdown{},m_pause_on_focus_loss{true},m_was_paused_by_focus_loss{},m_verbose_status{};
  static constexpr u32 FULLSCREEN_UI_CONTROLLER_POLLING_INTERVAL=8,BACKGROUND_CONTROLLER_POLLING_INTERVAL=100;
  bool isOnEmuThread() const {return QThread::currentThread()==thread();}
  bool shouldRenderToMain() const {return true;}
  QEventLoop* getEventLoop() {return m_event_loop;}
public Q_SLOTS:
  void setFullscreen(bool,bool);
  void setSurfaceless(bool);
  void shutdownVM(bool);
  void onApplicationStateChanged(Qt::ApplicationState);
  void doBackgroundControllerPoll();
  void loadSettings(SettingsInterface&,std::unique_lock<std::mutex>&);
  void startBackgroundControllerPollTimer();
  void stopBackgroundControllerPollTimer();
  void runOnCPUThread(const std::function<void()>&);
};
EmuThread* g_emu_thread{};
namespace Host {
void PumpMessagesOnCPUThread();
void RunOnCPUThread(std::function<void()>,bool=false);
}
#include "fullscreen.inc"
#include "surfaceless.inc"
#include "shutdown.inc"
#include "focus.inc"
#include "idle.inc"
#include "settings.inc"
#include "timer-start.inc"
#include "timer-stop.inc"
#include "pump.inc"
#include "slot.inc"
#include "dispatch.inc"
void reset(EmuThread& e) {
  e.timer.stop();e.m_is_fullscreen=false;e.m_is_rendering_to_main=false;e.m_is_surfaceless=false;
  e.m_save_state_on_shutdown=false;e.m_pause_on_focus_loss=true;e.m_was_paused_by_focus_loss=false;e.m_verbose_status=false;
  vm_state=VMState::Paused;MTGS::open=true;s_vm_locked_with_dialog=0;
}
void pumpUntil(const std::function<bool()>& done) {
  const auto until=Clock::now()+std::chrono::seconds(2);
  do {CHECK(Clock::now()<until);Host::PumpMessagesOnCPUThread();}while(!done());
}
void exercise_slots(EmuThread& e) {
  SettingsInterface settings;std::mutex mutex;
  for(unsigned op=0;op<8;++op)for(unsigned p=0;p<5;++p)for(unsigned delivery=0;delivery<2;++delivery) {
    reset(e);if(op==2)vm_state=VMState::Running;if(op==7)e.timer.start(1000);
    const auto initial_state=vm_state;
    std::unique_lock lock(mutex);start(p);bool called=false;
    at_release=[&] {
      CHECK(effects==0 && lock.owns_lock());CHECK(!e.m_is_fullscreen && !e.m_is_rendering_to_main && !e.m_is_surfaceless);
      CHECK(!e.m_save_state_on_shutdown && !e.m_was_paused_by_focus_loss && !e.m_verbose_status);
      CHECK(vm_state==initial_state);CHECK(e.timer.isActive()==(op==7));
    };
    auto operation=[&] {
      switch(op) {
        case 0:e.setFullscreen(true,true);break;
        case 1:e.setSurfaceless(true);break;
        case 2:e.onApplicationStateChanged(Qt::ApplicationInactive);break;
        case 3:e.doBackgroundControllerPoll();break;
        case 4:e.shutdownVM(true);break;
        case 5:e.loadSettings(settings,lock);break;
        case 6:e.startBackgroundControllerPollTimer();break;
        case 7:e.stopBackgroundControllerPollTimer();break;
      }
      called=true;
    };
    if(delivery==0)operation();
    else {CHECK(QMetaObject::invokeMethod(&e,operation,Qt::QueuedConnection));CHECK(!called);pumpUntil([&]{return called;});}
    CHECK(called);
    if(op==0)CHECK(e.m_is_fullscreen && e.m_is_rendering_to_main && effects==3);
    if(op==1)CHECK(e.m_is_surfaceless && effects==2);
    if(op==2)CHECK(e.m_was_paused_by_focus_loss && vm_state==VMState::Paused && effects==2);
    if(op==3)CHECK(effects==1);
    if(op==4)CHECK(e.m_save_state_on_shutdown && vm_state==VMState::Stopping && effects==1);
    if(op==5)CHECK(e.m_verbose_status && e.m_pause_on_focus_loss && effects==2);
    if(op==6)CHECK(e.timer.isActive() && e.timer.interval()==8 && effects==0);
    if(op==7)CHECK(!e.timer.isActive() && effects==0);
    hash(op);hash(effects);e.timer.stop();finish();
  }
}
void arbitrary(EmuThread& e) {
  for(unsigned kind=0;kind<4;++kind)for(unsigned p=0;p<5;++p) {
    reset(e);start(p);bool called=false;auto* receiver=new QObject;
    auto payload=std::make_shared<unsigned>(97);std::weak_ptr<unsigned> weak=payload;
    std::function<void()> callback=[payload,&called,kind] {
      CHECK(*payload==97);effect(10+kind);called=true;
      if(kind==3)Host::PumpMessagesOnCPUThread();
    };
    if(kind==1)QTimer::singleShot(0,receiver,callback);
    else CHECK(QMetaObject::invokeMethod(receiver,callback,Qt::QueuedConnection));
    payload.reset();callback={};CHECK(!weak.expired() && !called);
    if(kind==2) {delete receiver;receiver=nullptr;CHECK(weak.expired());Host::PumpMessagesOnCPUThread();CHECK(!called && effects==0);}
    else {pumpUntil([&]{return called;});CHECK(weak.expired() && effects==1);}
    delete receiver;finish();
  }
}
void callbacks(EmuThread& e) {
  for(unsigned inline_call=0;inline_call<2;++inline_call)for(unsigned p=0;p<5;++p) {
    reset(e);start(p);unsigned called=0;
    auto value=std::make_shared<unsigned>(67);std::weak_ptr<unsigned> weak=value;
    Host::RunOnCPUThread([value,&called]{CHECK(*value==67);effect(20);++called;},inline_call);
    value.reset();if(!inline_call)CHECK(!weak.expired() && called==0);
    if(!inline_call)pumpUntil([&]{return called!=0;});
    CHECK(called==1 && weak.expired());finish();
  }
}
void forwarding(EmuThread& e) {
  for(unsigned kind=0;kind<2;++kind) {
    reset(e);start(3);
    std::thread ui([&]{CHECK(!s_observer_cpu_thread && !e.isOnEmuThread());
      if(kind==0)e.setFullscreen(true,true);else e.setSurfaceless(true);
    });ui.join();
    CHECK(port.releases==0 && effects==0 && !e.m_is_fullscreen && !e.m_is_surfaceless);
    pumpUntil([&]{return kind==0?e.m_is_fullscreen:e.m_is_surfaceless;});
    CHECK(effects==(kind==0?3u:2u));finish();
  }
}
int main(int argc,char** argv) {
  QCoreApplication app(argc,argv);qRegisterMetaType<std::function<void()>>();
  cpu.set_online(true);s_observer_cpu_thread=true;EmuThread e;g_emu_thread=&e;
  exercise_slots(e);CHECK(cases==80);arbitrary(e);CHECK(cases==100);
  callbacks(e);forwarding(e);CHECK(cases==112);
  std::cout<<"{\"result\":\"PASS\",\"cases\":112,\"effects_digest\":\""<<std::hex<<digest
           <<"\",\"qt\":\""<<qVersion()<<"\"}\n";
}
#include "harness.moc"
