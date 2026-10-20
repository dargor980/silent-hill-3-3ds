// Own doubles and oracles; exact provider fragments remain private.
#include "check.hpp"
#include "sh3_observer/admission.hpp"
#include "sh3_observer/cpu_boundary.hpp"
#include "sh3_observer/pine_drain.hpp"
#include "sh3_observer/retained_drain.hpp"
#include "sh3_observer/host_epoch.hpp"
#include "sh3_observer/physical_writes.hpp"
#include <atomic>
#include <cstdio>
#include <functional>
#include <optional>
#include <string>
#include <thread>
#include <utility>
#include <vector>
using namespace sh3::observer;
using u64 = std::uint64_t;
#define __fi inline
#include "scoped-guard.inc"
namespace PINEServer {
[[maybe_unused]] static CooperativeGate s_observer_pine_gate;
[[maybe_unused]] static HostEpoch s_observer_pine_generation;
std::uint64_t GetObserverGeneration();
CooperativeGate::Closure BeginObserverExclusion(CooperativeGate::Clock::time_point);
}
#include "pine-bridge.inc"
#include "thread-state.inc"
enum class VMState { Shutdown, Initializing, Running, Paused, Resetting, Stopping };
std::atomic<VMState> s_state{VMState::Paused};
std::function<void()> during_state, during_qt;
bool unzip=true, recording=false;
bool s_cpu_implementation_changed = false;
[[maybe_unused]] struct { u64 cycle=1000; } cpuRegs;
struct Config {
  struct { struct {
    bool EnableEE=false, EnableIOP=false, EnableVU0=false, EnableVU1=false;
    bool EnableEECache=false, EnableFastmem=false;
  } Recompiler; } Cpu;
  struct { bool vuThread=false; } Speedhacks;
  struct { bool Enabled=false; } Achievements;
  bool EnablePINE=false, EnableDiscordPresence=false;
} EmuConfig;
bool dump=false, ra=false, pine=false, allocation=true, cpuinfo=true;
[[maybe_unused]] constexpr bool newVifDynaRec=true; // Same constant as the pinned provider.
std::function<void()> during_execute, during_effect;
std::vector<unsigned> effects;
unsigned cases=0; u64 digest=14695981039346656037ULL;
void effect(unsigned value) { effects.push_back(value); if(during_effect) during_effect(); }
struct CPU { void Execute() { effect(40); if(during_execute) during_execute(); } };
CPU intCpu, psxInt, CpuIntVU0, CpuIntVU1, other;
CPU *Cpu=&intCpu, *psxCpu=&psxInt, *CpuVU0=&CpuIntVU0, *CpuVU1=&CpuIntVU1;
namespace VMManager {
VMState GetState() { if(during_state) during_state(); return s_state.load(); }
void Execute();
namespace Internal {
bool CPUThreadInitialize(); void CPUThreadShutdown();
void ClearCPUExecutionCaches() { effect(42); }
#ifdef SH3_ENABLE_OBSERVER
AdmissionProfile SampleObserverAdmissionProfile();
CpuBoundary::Boundary EnterObserverCpuBoundary();
CpuBoundary::Activity EnterObserverCpuActivity();
void BeforeObserverProducer();
bool QueueObserverPineDrain(u64,std::chrono::milliseconds);
bool CancelObserverPineDrain(u64);
bool ObserverPineDrainPending();
bool PollObserverPineDrain();
PineDrain::Result GetObserverPineDrainResult();
#endif
}
}
namespace Threading {
void SetNameOfCurrentThread(const char*) { effect(1); }
struct ThreadHandle { static ThreadHandle GetForCallingThread() { return {}; } };
}
namespace PerformanceMetrics { void SetCPUThread(Threading::ThreadHandle) { effect(2); } }
struct FPControlRegister {
  static int GetDefault() { return 0; } static void SetCurrent(int) { effect(3); }
};
bool cpuinfo_initialize() { effect(4); return cpuinfo; }
struct Logger { void Error(const char*) { effect(5); } void Warning(const char*) { effect(6); } } Console;
void LogCPUCapabilities() { effect(7); }
namespace SysMemory {
bool Allocate() { effect(8); return allocation; }
void Release() { effect(9); }
}
namespace Host {
void WakeObserverPineDrain();
void RunOnCPUThread(std::function<void()>,bool=false);
void ReportErrorAsync(const char*, const char*) { effect(10); }
bool GetBaseBoolSettingValue(const char*, const char*, bool) { return false; }
}
void InitializeCPUProviders() { effect(11); } void ShutdownCPUProviders() { effect(12); }
void USBinit() { effect(13); } void USBshutdown() { effect(14); }
void LoadSettings() { effect(15); } void ReloadPINE() { effect(16); }
void InitializeDiscordPresence() { effect(17); } void ShutdownDiscordPresence() { effect(18); }
namespace Achievements {
void Initialize() { effect(19); } void Shutdown(bool) { effect(20); }
bool IsUsingRAIntegration() { return ra; }
}
namespace PINEServer { bool IsInitialized() { return pine; } void Deinitialize() { effect(21); } }
namespace GSDumpReplayer { bool IsReplayingDump() { return dump; } }
namespace InputManager { void CloseSources() { effect(22); } }
void WaitForSaveStateFlush() { effect(23); }
namespace MTGS { void ShutdownThread() { effect(24); } }
void GSJoinSnapshotThreads() { effect(25); }
constexpr int LOGLEVEL_NONE=0;
namespace Log { void SetFileOutputLevel(int, std::string) { effect(26); } }
struct { void ShutdownWorkerThread() { effect(27); } } R5900SymbolImporter;
void UpdateCPUImplementations() { effect(41); }
void vtlb_ResetFastmem() { effect(43); }
#include "initialize.inc"
#include "shutdown.inc"
#include "execute.inc"
#include "sample.inc"
constexpr auto bit(AdmissionCondition c) { return admission_bit(c); }
constexpr auto all = (std::uint32_t{1} << admission_condition_count)-1;
constexpr auto pending = bit(AdmissionCondition::pine_excluded)|bit(AdmissionCondition::rdebug_excluded)|
  bit(AdmissionCondition::gs_drained)|bit(AdmissionCondition::vu_drained)|bit(AdmissionCondition::other_writers_excluded);
constexpr auto vif = bit(AdmissionCondition::vif_dynarec_disabled);
void expected(std::uint32_t violations, std::uint32_t unknown) {
#ifdef SH3_ENABLE_OBSERVER
  const auto r=assess_profile(VMManager::Internal::SampleObserverAdmissionProfile());
  CHECK(r.violated==violations && r.unknown==unknown);
#else
  (void)violations; (void)unknown;
#endif
}
void check_not_cpu() { expected(bit(AdmissionCondition::cpu_thread), all^bit(AdmissionCondition::cpu_thread)); }
void check_executing() { expected(bit(AdmissionCondition::cpu_boundary), all^bit(AdmissionCondition::cpu_thread)^bit(AdmissionCondition::cpu_boundary)); }
void reset() {
  during_effect={}; during_execute={}; during_state={}; during_qt={}; unzip=true; recording=false; effects.clear(); EmuConfig={};
  dump=false; ra=false; pine=false; allocation=true; cpuinfo=true;
  Cpu=&intCpu; psxCpu=&psxInt; CpuVU0=&CpuIntVU0; CpuVU1=&CpuIntVU1;
  s_state=VMState::Paused; s_cpu_implementation_changed=false;
  VMManager::Internal::CPUThreadShutdown(); effects.clear();
}
template<class F> void run(F f) {
  reset(); f();
  for(auto value:effects) { digest^=value; digest*=1099511628211ULL; }
  digest^=effects.size(); digest*=1099511628211ULL; ++cases;
}

void expected_at_boundary(std::uint32_t violations, std::uint32_t unknown) {
#ifdef SH3_ENABLE_OBSERVER
  auto root=VMManager::Internal::EnterObserverCpuBoundary(); CHECK(root.valid());
#endif
  expected(violations,unknown);
}
struct Error { static void SetString(Error*, const char*) { effect(50); } };
#define TRANSLATE_STR(context, text) text
namespace VMManager { bool DoLoadState(const char*, Error*); void Reset() { effect(51); } }
namespace Host {
void OnSaveStateLoading(const char*) { effect(52); }
void OnSaveStateLoaded(const char*, bool) { effect(53); }
void PumpMessagesOnCPUThread();
}
bool SaveState_UnzipFromDisk(const char*, Error*) { effect(54); return unzip; }
struct {
  bool isActive() { return recording; }
  void handleLoadingSavestate() { effect(55); }
} g_InputRecording;
namespace MTGS { void PresentCurrentFrame() { effect(56); } }
namespace MemcardBusy { void CheckSaveStateDependency() { effect(57); } }
#include "load.inc"
unsigned wake_calls=0, timers_live=0, timers_started=0;
struct QEventLoop {
  void quit() { ++wake_calls; }
  static constexpr int AllEvents=0;
  void exec() { effect(60); if(during_qt) during_qt(); }
  void processEvents(int) { effect(61); if(during_qt) during_qt(); }
};
struct QTimer {
  QTimer() { ++timers_live; } ~QTimer() { --timers_live; }
  void setSingleShot(bool yes) { CHECK(yes); }
  void start(int interval) { CHECK(interval==1); ++timers_started; }
  void timeout() {}
};
struct QObject { template<class... T> static void connect(T&&...) {} };
struct Semaphore { void release() { effect(62); } };
namespace Qt { constexpr int QueuedConnection=0, BlockingQueuedConnection=1; }
#define Q_ARG(type, value) value
class EmuThread;
std::vector<std::function<void()>> cpu_queue;
struct QCoreApplication { static void quit() {} };
void* qApp=nullptr;
struct QMetaObject {
  static void invokeMethod(EmuThread*,const char*,int,const std::function<void()>&);
  static void invokeMethod(void*, void(*)(), int) { effect(63); }
};
void pxFailRel(const char*) { effect(64); throw 64; }
class EmuThread {
public:
  QEventLoop* m_event_loop{};
  Semaphore m_started_semaphore;
  std::atomic<bool> m_shutdown_flag{false};
  void* m_ui_thread{};
  ~EmuThread() { delete m_event_loop; }
  QEventLoop* getEventLoop() { return m_event_loop; }
  void connectSignals() { effect(65); }
  void createBackgroundControllerPollTimer() { effect(66); }
  void startBackgroundControllerPollTimer() { effect(67); }
  void stopBackgroundControllerPollTimer() { effect(68); }
  void destroyBackgroundControllerPollTimer() { effect(69); }
  void destroyVM() { effect(70); m_shutdown_flag=true; }
  void moveToThread(void*) { effect(71); }
  void deleteLater() { effect(72); }
  bool on_cpu=true;
  bool isOnEmuThread() const { return on_cpu; }
  void runOnCPUThread(const std::function<void()>&);
  void run();
};
EmuThread* g_emu_thread=nullptr;
void QMetaObject::invokeMethod(EmuThread* emu,const char*,int,const std::function<void()>& fn) {
  cpu_queue.emplace_back([emu,fn] { emu->runOnCPUThread(fn); });
}
#include "qt-slot.inc"
#include "qt-dispatch.inc"
#include "qt-wake.inc"
#include "qt-run.inc"
#include "qt-pump.inc"
void check_dispatch() {
  check_executing();
#ifdef SH3_ENABLE_OBSERVER
  auto no=VMManager::Internal::EnterObserverCpuBoundary(); CHECK(!no.valid());
#endif
}
void provider_cases() {
  // Full DoLoadState body: early rejection, failed unzip, success, recording, unwind.
  for(unsigned mode=0;mode<5;++mode) run([=] {
    CHECK(VMManager::Internal::CPUThreadInitialize());
    dump=mode==0; unzip=mode!=1; recording=mode==3;
#ifdef SH3_ENABLE_OBSERVER
    auto root=VMManager::Internal::EnterObserverCpuBoundary(); CHECK(root.valid());
#endif
    during_effect=[=] { check_dispatch(); if(mode==4) throw 4; };
    bool caught=false, result=false;
    try { result=VMManager::DoLoadState("synthetic",nullptr); } catch(int e) { caught=e==4; }
    during_effect={}; CHECK(caught==(mode==4)); CHECK(result==(mode==2 || mode==3));
#ifdef SH3_ENABLE_OBSERVER
    CHECK(!root.valid()); check_executing();
#endif
  });
  // Full Qt run body with a controlled event-loop double, never the real Qt loop.
  for(auto state:{VMState::Paused,VMState::Running,VMState::Shutdown,VMState::Stopping}) run([=] {
    s_state=state; EmuThread emu; unsigned starts=0, callbacks=0;
    during_state=[&] {
#ifdef SH3_ENABLE_OBSERVER
      CHECK(s_observer_cpu_boundary.at_boundary());
#endif
      ++starts;
    };
    during_qt=[&] { check_dispatch(); ++callbacks; emu.m_shutdown_flag=true; };
    during_execute=check_dispatch;
    emu.run(); during_state={}; during_execute={}; during_qt={};
    CHECK(starts==1); CHECK(callbacks==(state==VMState::Stopping?0u:1u)); check_not_cpu();
  });
  run([] { allocation=false; EmuThread emu; emu.run(); check_not_cpu(); });
  run([] {
    CHECK(VMManager::Internal::CPUThreadInitialize()); EmuThread emu;
    emu.m_event_loop=new QEventLoop; g_emu_thread=&emu;
#ifdef SH3_ENABLE_OBSERVER
    auto root=VMManager::Internal::EnterObserverCpuBoundary(); CHECK(root.valid());
#endif
    during_qt=check_dispatch; Host::PumpMessagesOnCPUThread(); during_qt={}; g_emu_thread=nullptr;
#ifdef SH3_ENABLE_OBSERVER
    CHECK(!root.valid()); check_executing();
#endif
  });
}
void boundary_cases() {
#ifdef SH3_ENABLE_OBSERVER
  run([] { CHECK(VMManager::Internal::CPUThreadInitialize()); check_executing(); });
  run([] { CHECK(VMManager::Internal::CPUThreadInitialize());
    { auto root=VMManager::Internal::EnterObserverCpuBoundary(); expected(vif,pending);
      { auto nested=VMManager::Internal::EnterObserverCpuBoundary(); CHECK(!nested.valid()); }
      CHECK(!root.valid()); check_executing(); }
    expected_at_boundary(vif,pending);
  });
  run([] { CHECK(VMManager::Internal::CPUThreadInitialize());
    { auto root=VMManager::Internal::EnterObserverCpuBoundary();
      { auto busy=VMManager::Internal::EnterObserverCpuActivity(); check_dispatch(); }
      CHECK(!root.valid()); check_dispatch(); }
    expected_at_boundary(vif,pending);
  });
  run([] { CHECK(VMManager::Internal::CPUThreadInitialize());
    auto root=VMManager::Internal::EnterObserverCpuBoundary();
    during_execute=check_dispatch; VMManager::Execute(); CHECK(!root.valid()); check_executing();
  });
  run([] { CHECK(VMManager::Internal::CPUThreadInitialize());
    auto root=VMManager::Internal::EnterObserverCpuBoundary();
    VMManager::Internal::CPUThreadShutdown(); CHECK(!root.valid()); check_not_cpu();
    CHECK(VMManager::Internal::CPUThreadInitialize()); CHECK(!root.valid()); check_executing();
  });
#endif
}


void coordinator_cases() {
#ifdef SH3_ENABLE_OBSERVER
  using namespace VMManager::Internal;
  using S=PineDrain::State;
  static u64 request_id=100;
  run([] {
    CHECK(!QueueObserverPineDrain(++request_id,std::chrono::seconds(1)));
    CHECK(!CancelObserverPineDrain(request_id)); CHECK(!PollObserverPineDrain());
    CHECK(GetObserverPineDrainResult().state==S::idle);
    CHECK(CPUThreadInitialize());
    for(auto timeout:{std::chrono::milliseconds(0),std::chrono::milliseconds(-1),std::chrono::milliseconds(5001)})
      CHECK(!QueueObserverPineDrain(++request_id,timeout));
    s_state=VMState::Running; CHECK(!QueueObserverPineDrain(++request_id,std::chrono::seconds(1)));
    s_state=VMState::Paused;
    std::thread other([] { CHECK(!QueueObserverPineDrain(1,std::chrono::seconds(1))); CHECK(!ObserverPineDrainPending()); }); other.join();
  });
  // Real inline and queued dispatch bodies revoke before invoking callbacks.
  for(bool inline_call:{false,true}) run([=] {
    CHECK(CPUThreadInitialize()); EmuThread emu; emu.m_event_loop=new QEventLoop; g_emu_thread=&emu;
    auto root=EnterObserverCpuBoundary(); unsigned calls=0;
    Host::RunOnCPUThread([&] { check_dispatch(); ++calls; },inline_call);
    if(!inline_call) { CHECK(root.valid()); CHECK(calls==0); CHECK(cpu_queue.size()==1); cpu_queue.front()(); cpu_queue.clear(); }
    CHECK(calls==1); CHECK(!root.valid()); g_emu_thread=nullptr;
  });
  // The full CPU loop drives the real coordinator; event dispatch itself is doubled.
  for(unsigned mode=0;mode<8;++mode) run([=] {
    EmuThread emu; g_emu_thread=&emu; unsigned phase=0;
    auto work=PINEServer::s_observer_pine_gate.enter(); CHECK(work);
    const auto id=++request_id; const unsigned old_timers=timers_started;
    if(mode==7)s_state=VMState::Running;
    during_execute=[] { CHECK(false); };
    during_qt=[&] {
      if(phase==0) {
        if(mode==7)s_state=VMState::Paused;
        CHECK(QueueObserverPineDrain(id,mode==3?std::chrono::milliseconds(20):std::chrono::seconds(5)));
        CHECK(!QueueObserverPineDrain(id+1,std::chrono::seconds(1)));
        CHECK(!CancelObserverPineDrain(id+1)); CHECK(ObserverPineDrainPending());
        CHECK(PINEServer::s_observer_pine_gate.enter()); // Only queued, not admitted yet.
      } else if(phase==1) {
        CHECK(timers_live==1); CHECK(!PINEServer::s_observer_pine_gate.enter());
        if(mode==0 || mode==7) {
          Host::RunOnCPUThread([work] { CHECK(work); check_dispatch(); }); work={};
          cpu_queue.front()(); cpu_queue.clear();
        } else if(mode==1) { std::vector<CooperativeGate::Work> discarded{work}; work={}; discarded.clear(); }
        else if(mode==2) { CHECK(CancelObserverPineDrain(id)); CHECK(!PINEServer::s_observer_pine_gate.enter()); }
        else if(mode==3)std::this_thread::sleep_for(std::chrono::milliseconds(25));
        else if(mode==4) { PINEServer::s_observer_pine_generation.advance(); PINEServer::s_observer_pine_generation.advance(); }
        else if(mode==5)before_lifecycle(LifetimeKind::reset,1000);
        else if(mode==6)emu.m_shutdown_flag=true;
      } else {
        CHECK(phase==2); const auto result=GetObserverPineDrainResult(); CHECK(result.id==id);
        const auto want=(mode<=1 || mode==7)?S::rejected:mode==2?S::cancelled:mode==3?S::timed_out:S::invalidated;
        CHECK(result.state==want); CHECK(!ObserverPineDrainPending()); CHECK(PINEServer::s_observer_pine_gate.enter());
        emu.m_shutdown_flag=true;
      }
      ++phase;
    };
    emu.run(); during_qt={}; during_execute={}; g_emu_thread=nullptr;
    CHECK(phase==(mode==6?2u:3u)); CHECK(timers_live==0); CHECK(timers_started==old_timers+1);
    CHECK(PINEServer::s_observer_pine_gate.enter());
    if(mode==6)CHECK(s_observer_pine_result.state==S::cancelled);
  });
#endif
}


void retained_cases() {
#ifdef SH3_ENABLE_OBSERVER
  using namespace VMManager::Internal;
  using S=PineDrain::State;
  static u64 request_id=1000;
  // Real transition bodies cancel before the first original effect.
  for(int phase=0;phase<3;++phase)for(bool load:{false,true}) run([=] {
    CHECK(CPUThreadInitialize()); EmuThread emu; emu.m_event_loop=new QEventLoop; g_emu_thread=&emu;
    auto work=PINEServer::s_observer_pine_gate.enter(); CHECK(work);
    const auto id=++request_id; CHECK(QueueObserverPineDrain(id,std::chrono::seconds(5)));
    if(phase>0) {
      auto root=EnterObserverCpuBoundary();
      CHECK(s_observer_pine_drain.step(true,{host_epoch(),PINEServer::GetObserverGeneration()})==S::draining);
    }
    if(phase==2) {
      work={}; auto root=EnterObserverCpuBoundary();
      CHECK(s_observer_pine_drain.step(true,{host_epoch(),PINEServer::GetObserverGeneration()})==S::rejected);
      CHECK(s_observer_pine_drain.effects_started()); // Partial phase retained until retire.
    }
    unsigned effects_seen=0;
    during_effect=[&] {
      CHECK(!ObserverPineDrainPending()); CHECK(PINEServer::s_observer_pine_gate.enter());
      const auto result=GetObserverPineDrainResult(); CHECK(result.id==id);
      CHECK(result.state==(phase==2?S::rejected:S::cancelled)); ++effects_seen;
    };
    if(load) { Error error; CHECK(VMManager::DoLoadState("synthetic",&error)); }
    else VMManager::Execute();
    during_effect={}; CHECK(effects_seen>0); g_emu_thread=nullptr;
  });
  // Ordinary callbacks still drain old PINE work, but release an initiated
  // downstream phase before entering their original body.
  for(bool started:{false,true})for(bool inline_call:{false,true}) run([=] {
    CHECK(CPUThreadInitialize()); EmuThread emu; emu.m_event_loop=new QEventLoop; g_emu_thread=&emu;
    auto work=PINEServer::s_observer_pine_gate.enter(); CHECK(work);
    const auto id=++request_id; CHECK(QueueObserverPineDrain(id,std::chrono::seconds(5)));
    { auto root=EnterObserverCpuBoundary();
      CHECK(s_observer_pine_drain.step(true,{host_epoch(),PINEServer::GetObserverGeneration()})==S::draining); }
    if(started) {
      work={}; auto root=EnterObserverCpuBoundary();
      CHECK(s_observer_pine_drain.step(true,{host_epoch(),PINEServer::GetObserverGeneration()})==S::rejected);
    }
    unsigned calls=0;
    Host::RunOnCPUThread([&] {
      ++calls; CHECK(ObserverPineDrainPending()!=started);
      CHECK(bool(PINEServer::s_observer_pine_gate.enter())==started);
      if(started)CHECK(GetObserverPineDrainResult().id==id);
    },inline_call);
    if(!inline_call) { CHECK(calls==0); cpu_queue.front()(); cpu_queue.clear(); }
    CHECK(calls==1); StopObserverPineDrain(); g_emu_thread=nullptr;
  });
#endif
}

int main() {
  run([] { check_not_cpu(); });
  run([] { allocation=false; CHECK(!VMManager::Internal::CPUThreadInitialize()); check_not_cpu(); });
  run([] { cpuinfo=false; CHECK(VMManager::Internal::CPUThreadInitialize()); expected_at_boundary(vif,pending); });
  run([] { during_effect=check_not_cpu; CHECK(VMManager::Internal::CPUThreadInitialize()); during_effect={}; expected_at_boundary(vif,pending); });
  run([] { CHECK(VMManager::Internal::CPUThreadInitialize()); during_effect=check_not_cpu; VMManager::Internal::CPUThreadShutdown(); during_effect={}; check_not_cpu(); });
  run([] { CHECK(VMManager::Internal::CPUThreadInitialize()); std::thread t(check_not_cpu); t.join(); expected_at_boundary(vif,pending); });
  for(auto state:{VMState::Shutdown,VMState::Initializing,VMState::Running,VMState::Resetting,VMState::Stopping})
    run([=] { CHECK(VMManager::Internal::CPUThreadInitialize()); s_state=state; expected_at_boundary(bit(AdmissionCondition::paused), all^bit(AdmissionCondition::cpu_thread)^bit(AdmissionCondition::cpu_boundary)^bit(AdmissionCondition::paused)); });
  const AdmissionCondition modes[]={AdmissionCondition::ee_interpreter,AdmissionCondition::iop_interpreter,AdmissionCondition::vu0_interpreter,AdmissionCondition::vu1_interpreter};
  for(unsigned i=0;i<4;++i) {
    run([=] { CHECK(VMManager::Internal::CPUThreadInitialize()); bool* options[]={&EmuConfig.Cpu.Recompiler.EnableEE,&EmuConfig.Cpu.Recompiler.EnableIOP,&EmuConfig.Cpu.Recompiler.EnableVU0,&EmuConfig.Cpu.Recompiler.EnableVU1}; *options[i]=true; expected_at_boundary(vif|bit(modes[i]),pending); });
    for(bool null:{false,true}) run([=] { CHECK(VMManager::Internal::CPUThreadInitialize()); CPU** cpus[]={&Cpu,&psxCpu,&CpuVU0,&CpuVU1}; *cpus[i]=null?nullptr:&other; expected_at_boundary(vif|bit(modes[i]),pending); });
  }
  run([] { CHECK(VMManager::Internal::CPUThreadInitialize()); dump=true; expected_at_boundary(vif|bit(AdmissionCondition::ee_interpreter),pending); });
  run([] { CHECK(VMManager::Internal::CPUThreadInitialize()); s_cpu_implementation_changed=true; expected_at_boundary(vif|bit(AdmissionCondition::implementations_settled),pending); });
  run([] { CHECK(VMManager::Internal::CPUThreadInitialize()); EmuConfig.Cpu.Recompiler.EnableEECache=true; EmuConfig.Cpu.Recompiler.EnableFastmem=true; EmuConfig.Speedhacks.vuThread=true; ra=true; expected_at_boundary(vif|bit(AdmissionCondition::ee_cache_disabled)|bit(AdmissionCondition::fastmem_disabled)|bit(AdmissionCondition::mtvu_disabled)|bit(AdmissionCondition::raintegration_disabled),pending); });
  for(unsigned flags=0;flags<4;++flags) run([=] { CHECK(VMManager::Internal::CPUThreadInitialize()); EmuConfig.EnablePINE=flags&1; pine=flags&2; expected_at_boundary(vif|(flags?bit(AdmissionCondition::pine_excluded):0),pending^(flags?bit(AdmissionCondition::pine_excluded):0)); });
  run([] { CHECK(VMManager::Internal::CPUThreadInitialize()); during_execute=check_executing; VMManager::Execute(); expected_at_boundary(vif,pending); });
  run([] { CHECK(VMManager::Internal::CPUThreadInitialize()); s_cpu_implementation_changed=true; during_effect=check_executing; VMManager::Execute(); during_effect={}; CHECK(!s_cpu_implementation_changed); expected_at_boundary(vif,pending); });
  run([] { CHECK(VMManager::Internal::CPUThreadInitialize()); during_execute=[]{check_executing(); throw 7;}; bool caught=false; try { VMManager::Execute(); } catch(int e) { caught=e==7; } CHECK(caught); expected_at_boundary(vif,pending); });
  run([] { CHECK(VMManager::Internal::CPUThreadInitialize()); unsigned depth=0; during_execute=[&]{check_executing(); if(++depth==1)VMManager::Execute(); check_executing();}; VMManager::Execute(); CHECK(depth==2); expected_at_boundary(vif,pending); });
  CHECK(cases==34); provider_cases(); CHECK(cases==45);
  const auto common_digest=digest; const unsigned common_cases=cases;
  boundary_cases(); coordinator_cases(); retained_cases();
  std::printf("{\"common_cases\":%u,\"extra_cases\":%u,\"result\":\"PASS\",\"effects_digest\":\"%016llx\"}\n",common_cases,cases-common_cases,static_cast<unsigned long long>(common_digest));
}
