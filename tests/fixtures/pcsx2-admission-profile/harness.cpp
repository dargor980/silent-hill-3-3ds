// Own doubles and oracles; exact provider fragments remain private.
#include "check.hpp"
#include "sh3_observer/admission.hpp"
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
#include "thread-state.inc"
enum class VMState { Shutdown, Initializing, Running, Paused, Resetting, Stopping };
std::atomic<VMState> s_state{VMState::Paused};
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
VMState GetState() { return s_state.load(); }
void Execute();
namespace Internal {
bool CPUThreadInitialize(); void CPUThreadShutdown();
void ClearCPUExecutionCaches() { effect(42); }
#ifdef SH3_ENABLE_OBSERVER
AdmissionProfile SampleObserverAdmissionProfile();
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
  during_effect={}; during_execute={}; effects.clear(); EmuConfig={};
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
int main() {
  run([] { check_not_cpu(); });
  run([] { allocation=false; CHECK(!VMManager::Internal::CPUThreadInitialize()); check_not_cpu(); });
  run([] { cpuinfo=false; CHECK(VMManager::Internal::CPUThreadInitialize()); expected(vif,pending); });
  run([] { during_effect=check_not_cpu; CHECK(VMManager::Internal::CPUThreadInitialize()); during_effect={}; expected(vif,pending); });
  run([] { CHECK(VMManager::Internal::CPUThreadInitialize()); during_effect=check_not_cpu; VMManager::Internal::CPUThreadShutdown(); during_effect={}; check_not_cpu(); });
  run([] { CHECK(VMManager::Internal::CPUThreadInitialize()); std::thread t(check_not_cpu); t.join(); expected(vif,pending); });
  for(auto state:{VMState::Shutdown,VMState::Initializing,VMState::Running,VMState::Resetting,VMState::Stopping})
    run([=] { CHECK(VMManager::Internal::CPUThreadInitialize()); s_state=state; expected(bit(AdmissionCondition::paused), all^bit(AdmissionCondition::cpu_thread)^bit(AdmissionCondition::cpu_boundary)^bit(AdmissionCondition::paused)); });
  const AdmissionCondition modes[]={AdmissionCondition::ee_interpreter,AdmissionCondition::iop_interpreter,AdmissionCondition::vu0_interpreter,AdmissionCondition::vu1_interpreter};
  for(unsigned i=0;i<4;++i) {
    run([=] { CHECK(VMManager::Internal::CPUThreadInitialize()); bool* options[]={&EmuConfig.Cpu.Recompiler.EnableEE,&EmuConfig.Cpu.Recompiler.EnableIOP,&EmuConfig.Cpu.Recompiler.EnableVU0,&EmuConfig.Cpu.Recompiler.EnableVU1}; *options[i]=true; expected(vif|bit(modes[i]),pending); });
    for(bool null:{false,true}) run([=] { CHECK(VMManager::Internal::CPUThreadInitialize()); CPU** cpus[]={&Cpu,&psxCpu,&CpuVU0,&CpuVU1}; *cpus[i]=null?nullptr:&other; expected(vif|bit(modes[i]),pending); });
  }
  run([] { CHECK(VMManager::Internal::CPUThreadInitialize()); dump=true; expected(vif|bit(AdmissionCondition::ee_interpreter),pending); });
  run([] { CHECK(VMManager::Internal::CPUThreadInitialize()); s_cpu_implementation_changed=true; expected(vif|bit(AdmissionCondition::implementations_settled),pending); });
  run([] { CHECK(VMManager::Internal::CPUThreadInitialize()); EmuConfig.Cpu.Recompiler.EnableEECache=true; EmuConfig.Cpu.Recompiler.EnableFastmem=true; EmuConfig.Speedhacks.vuThread=true; ra=true; expected(vif|bit(AdmissionCondition::ee_cache_disabled)|bit(AdmissionCondition::fastmem_disabled)|bit(AdmissionCondition::mtvu_disabled)|bit(AdmissionCondition::raintegration_disabled),pending); });
  for(unsigned flags=0;flags<4;++flags) run([=] { CHECK(VMManager::Internal::CPUThreadInitialize()); EmuConfig.EnablePINE=flags&1; pine=flags&2; expected(vif|(flags?bit(AdmissionCondition::pine_excluded):0),pending^(flags?bit(AdmissionCondition::pine_excluded):0)); });
  run([] { CHECK(VMManager::Internal::CPUThreadInitialize()); during_execute=check_executing; VMManager::Execute(); expected(vif,pending); });
  run([] { CHECK(VMManager::Internal::CPUThreadInitialize()); s_cpu_implementation_changed=true; during_effect=check_executing; VMManager::Execute(); during_effect={}; CHECK(!s_cpu_implementation_changed); expected(vif,pending); });
  run([] { CHECK(VMManager::Internal::CPUThreadInitialize()); during_execute=[]{check_executing(); throw 7;}; bool caught=false; try { VMManager::Execute(); } catch(int e) { caught=e==7; } CHECK(caught); expected(vif,pending); });
  run([] { CHECK(VMManager::Internal::CPUThreadInitialize()); unsigned depth=0; during_execute=[&]{check_executing(); if(++depth==1)VMManager::Execute(); check_executing();}; VMManager::Execute(); CHECK(depth==2); expected(vif,pending); });
  std::printf("{\"cases\":%u,\"result\":\"PASS\",\"effects_digest\":\"%016llx\"}\n",cases,static_cast<unsigned long long>(digest));
}
