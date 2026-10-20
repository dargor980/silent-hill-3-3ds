// Own support derived from the SRC83 fixture; PINE now uses the real server.
#include "sh3_observer/cooperative_gate.hpp"
#include "sh3_observer/pine_drain.hpp"
#include "PINE.h"
// Own fixture. All provider bodies are exact fragments from a private checkout.
#include "check.hpp"
#include "sh3_observer/worker_control.hpp"
#include "sh3_observer/cpu_boundary.hpp"
#include "sh3_observer/worker_drain.hpp"
#include <atomic>
#include <cassert>
#include <chrono>
#include <cstdint>
#include <cstdio>
#include <cstring>
#include <functional>
#include <limits>
#include <list>
#include <mutex>
#include <semaphore>
#include <string_view>
#include <thread>
#include <vector>
#include <mach/mach.h>
#include <mach/mach_error.h>
#include <mach/semaphore.h>
#include <mach/task.h>
using u8 = std::uint8_t; using u32 = std::uint32_t; using u64 = std::uint64_t;
using s32 = std::int32_t; using uptr = std::uintptr_t; using uint = unsigned;
struct alignas(16) u128 { u32 words[4]; };
using Control = sh3::observer::WorkerControl; using Token = Control::Token; using Status = Control::Status;
using namespace std::chrono_literals;
#define pxAssert(x) CHECK(x)
#define pxAssertMsg(x, msg) CHECK(x)
#define pxAssertRel(x, msg) CHECK(x)
#define pxFailRel(msg) CHECK(false)
#define __ri
#define MTVU_ALWAYS_KICK 0
#define MTVU_SYNC_MODE 0
#define __fi
#define __cachelinesize 64
#define jNO_DEFAULT default: CHECK(false)
#define MTGS_LOG(...)
#define MTVU_LOG(...)
#define COPY_GS_PACKET_TO_MTGS 0
constexpr bool IsDevBuild = false;
namespace Threading {
#include "kernel_class.inc"
// Expose only WorkSema state for a deterministic test of a sleeping native worker.
#define class struct
#include "work_sema_class.inc"
#undef class
using ThreadHandle = std::thread;
class Thread : public ThreadHandle {
public:
  bool Joinable() const { return joinable(); }
  void SetStackSize(unsigned) {}
  template<class F> void Start(F f) { ThreadHandle::operator=(std::thread(f)); }
  void Join() { join(); }
};
void SetNameOfCurrentThread(const char*) {}
void SpinWait() { std::this_thread::yield(); }
class UserspaceSemaphore {
  std::counting_semaphore<1024> semaphore_{0};
public:
  std::atomic<unsigned> posts{0};
  std::function<void()> before_post;
  void Post() { if (before_post) before_post(); posts.fetch_add(1); semaphore_.release(); }
  void Wait() { semaphore_.acquire(); }
  bool TryWait() { return semaphore_.try_acquire(); }
};
}
#include "kernel_darwin.inc"
#include "check_for_work.inc"
#include "wait_for_work.inc"
#include "wait_for_empty.inc"
#include "kill.inc"
#include "reset.inc"

// Effect/type doubles, not provider ABI or renderer implementations.
namespace Ps2MemSize { constexpr unsigned GSregs = 8192; }
alignas(16) u8 PS2MEM_GS[Ps2MemSize::GSregs]{};
enum class FreezeAction { Load, Save };
enum class GSVSyncMode { Off };
enum class GSInterlaceMode { Off };
enum GIF_PATH { GIF_PATH_1, GIF_PATH_2, GIF_PATH_3 };
struct GSRegSIGBLID { u64 value; };
struct freezeData { unsigned value; };
struct GSConfig { bool SynchronousMTGS = false; int Renderer = 0; };
struct { GSConfig GS; } EmuConfig;
enum class VMState { Shutdown, Running, Paused };
std::atomic<VMState> vm_state{VMState::Paused};
thread_local bool s_observer_cpu_thread = false;
thread_local sh3::observer::CpuBoundary s_observer_cpu_boundary;
namespace VMManager {
constexpr unsigned EMU_THREAD_STACK_SIZE = 0;
VMState GetState() { return vm_state.load(); }
GSVSyncMode GetEffectiveVSyncMode() { return GSVSyncMode::Off; }
bool ShouldAllowPresentThrottle() { return true; }
namespace Internal { bool IsObserverCpuThread(); bool CanRequestObserverWorker(); void BeforeObserverProducer();
bool WaitObserverWorkerDrain(); bool QueueObserverPineDrain(u64,std::chrono::milliseconds);bool CancelObserverPineDrain(u64);
bool ObserverPineDrainPending();bool PollObserverPineDrain();sh3::observer::PineDrain::Result GetObserverPineDrainResult();
sh3::observer::CpuBoundary::Activity EnterObserverCpuActivity(); }
}
namespace PageFaultHandler { void InstallSecondaryThread() {} }
struct FPControlRegister { static int GetDefault() { return 0; } static void SetCurrent(int) {} };
constexpr int Color_Red=1;
struct ConsoleDouble {template<class... T>void WriteLn(T&&...){}template<class... T>void Error(T&&...){}} Console;
std::atomic<unsigned> opened{0}, closed{0}, callbacks{0}, resets{0}, soft_resets{0}, transfers{0}, vsyncs{0}, presents{0}, throttles{0};
std::atomic_bool open_success{true}, block_open{false}, block_idle{false};
std::binary_semaphore open_entered(0), open_go(0), idle_entered(0), idle_go(0);
bool GSopen(const GSConfig&, int, u8*, GSVSyncMode, bool);
void GSclose();
bool GSHasDisplayWindow() { return true; }
void GSPresentCurrentFrame() {
  if (block_idle.load()) { idle_entered.release(); idle_go.acquire(); }
  presents.fetch_add(1);
}
void GSThrottlePresentation() { throttles.fetch_add(1); }
void GSreset(bool) { resets.fetch_add(1); }
void GSgifSoftReset(int) { soft_resets.fetch_add(1); }
void GSgifTransfer(u8*, unsigned qwc) { transfers.fetch_add(qwc); }
void GSvsync(int, bool) { vsyncs.fetch_add(1); }
int GSfreeze(FreezeAction, freezeData* p) { p->value = 41; return 9; }
void GSInitAndReadFIFO(u8* p, unsigned qwc) { std::memset(p, 0x5a, qwc * 16); }
void MemCopy_WrappedSrc(const u128* source, unsigned& pos, unsigned size, u128* dest, unsigned count) {
  for (unsigned i = 0; i < count; ++i) { dest[i] = source[pos]; pos = (pos + 1) % size; }
}
constexpr int _1mb=1024*1024, _4kb=4096, REG_TPC=0, vu1RunCycles=7;
std::atomic<unsigned> effects{0},executions{0},finished{0},clears{0},unpacked{0};
std::atomic_bool block_execute{false},block_gs{false};
std::binary_semaphore execute_entered(0),execute_go(0),gs_entered(0),gs_space(0);
struct REG_VI { u32 UL; };
struct VECTOR { u32 words[4]; };
struct vifStruct { u32 tag[4]; u32 StructEnd; u32 MaskCol[4], MaskRow[4]; };
struct VIFregisters { u32 cycle, mode, num, mask, itop, top; };
using VIFregistersMTVU = VIFregisters;
struct { u32 cycle; REG_VI VI[32]; VECTOR VF[32]; u8 Micro[256], Mem[256]; } VU1{};
struct CpuDouble {
  void SetStartPC(u32 pc) { CHECK(pc == 24); }
  void Execute(int cycles) {
    CHECK(cycles == vu1RunCycles);
    if (block_execute.load()) { execute_entered.release(); execute_go.acquire(); }
    executions.fetch_add(1); effects.store(1); VU1.cycle = 47;
  }
  void Clear(u32 address, u32 size) { CHECK(address == 8 && size == 4); clears.fetch_add(1); }
} cpu_double;
CpuDouble* CpuVU1 = &cpu_double;
struct GS_Packet { u32 offset, size, readAmount; };
struct Gif_Path {
  void FinishGSPacketMTVU() {
    if(block_gs.load()){gs_entered.release();gs_space.acquire();}
    finished.fetch_add(1);effects.store(2);
  }
  alignas(16) u8 buffer[256]{};
  std::atomic<unsigned> readAmount{0}, popped{0};
  GS_Packet packet{0, 16, 16};
  GS_Packet GetGSPacketMTVU() { return packet; }
  void PopGSPacketMTVU() { popped.fetch_add(1); }
  unsigned GetPendingGSPackets() { return 1 - popped.load(); }
};
struct { Gif_Path gifPath[3]; } gifUnit;
void MTVU_Unpack(void* data, VIFregisters& regs) {
  CHECK(*static_cast<u32*>(data) == 0x55667788 && regs.top == 29); unpacked.fetch_add(1);
}
static u32 size_u32(u32 x) { return (x + 3) >> 2; }
#include "commands.inc"

#define class struct
#define private public
#include "vu_class.inc"
#undef private
#undef class
extern VU_Thread vu1Thread;
#include "gs_header.inc"
#include "gs_state.inc"
#include "packet_tag.inc"
#include "gs_control.inc"
using Clock=sh3::observer::PineDrain::Clock;
using State=sh3::observer::PineDrain::State;
sh3::observer::CooperativeGate::Work enter_pine();
struct PineAccess {auto enter(){return enter_pine();}} pine_gate;
std::uint64_t host_generation=7;
namespace sh3::observer { std::uint64_t host_epoch() noexcept {return host_generation;} }
namespace Host {void WakeObserverPineDrain(){}}
#include "owner.inc"
#include "stop_owner.inc"
#include "cpu_actor.inc"
#include "cpu_guard.inc"
#include "before_producer.inc"
#include "wait_control.inc"
#include "queue.inc"
#include "cancel.inc"
#include "pending.inc"
#include "result.inc"
#include "poll.inc"
#include "activity.inc"
#include "vu_control.inc"
#include "constructor.inc"
#include "destructor.inc"
#include "open.inc"
#include "close.inc"
#include "vu_reset.inc"
#include "execute.inc"
#include "wait_size.inc"
#include "reserve.inc"
#include "read_pos.inc"
#include "write_pos.inc"
#include "write_ptr.inc"
#include "commit_write.inc"
#include "commit_read.inc"
#include "read_word.inc"
#include "read_bytes.inc"
#include "read_regs.inc"
#include "write_word.inc"
#include "write_bytes.inc"
#include "write_regs.inc"
#include "kick.inc"
#include "done.inc"
#include "wait_vu.inc"
#include "write_data.inc"
VU_Thread vu1Thread;

#include "gs_open_query.inc"
#include "gs_start.inc"
#include "gs_shutdown.inc"
#include "gs_entry.inc"
#include "gs_main.inc"
#include "gs_open.inc"
#include "gs_close.inc"
#include "gs_wait.inc"
#include "gs_event.inc"
#include "gs_stall.inc"
#include "gs_finish.inc"
#include "gs_simple.inc"
#include "gs_pointer.inc"
#include "gs_async.inc"
#include "gs_idle.inc"

bool GSopen(const GSConfig&, int, u8*, GSVSyncMode, bool) {
  CHECK(!MTGS::GetObserverLifecycle().online);
  if (block_open.load()) { open_entered.release(); open_go.acquire(); }
  if (open_success.load()) { opened.fetch_add(1); return true; }
  return false;
}
void GSclose() { CHECK(!MTGS::GetObserverLifecycle().online); closed.fetch_add(1); }

#include <QCoreApplication>
#include <QEventLoop>
#include <QTimer>
#include <memory>
#include <string>

template<class P> void until(P ready) {
  const auto end=Clock::now()+3s;
  while(!ready()){CHECK(Clock::now()<end);std::this_thread::yield();}
}
void start(unsigned generation=1) {
  CHECK(MTGS::WaitForOpen());vu1Thread.Open();
  until([&]{return vu1Thread.GetObserverLifecycle().online;});
  CHECK(vu1Thread.GetObserverLifecycle().generation==generation);
  CHECK(MTGS::GetObserverLifecycle().generation==generation);
}
void close_all() {
  StopObserverPineDrain();vu1Thread.Close();MTGS::ShutdownThread();
  CHECK(!vu1Thread.GetObserverLifecycle().online && !MTGS::GetObserverLifecycle().online);
  CHECK(!s_observer_pine_drain.active() && pine_gate.enter());
}
void execute_packet() {
  vu1Thread.Write(MTVU_VU_EXECUTE);vu1Thread.Write(3);vu1Thread.Write(11);
  vu1Thread.Write(13);vu1Thread.Write(17);vu1Thread.CommitWritePos();
}
State step() {
  auto b=s_observer_cpu_boundary.enter();CHECK(b.valid());
  return s_observer_pine_drain.step(true,{host_generation,PINEServer::GetObserverGeneration()});
}
void queue(std::uint64_t id=1,std::chrono::milliseconds timeout=2000ms) {
  CHECK(VMManager::Internal::QueueObserverPineDrain(id,timeout));
}
void wait_held() {until([]{return step()==State::held;});CHECK(!pine_gate.enter());}
void check_released(Token vu={1,1},Token gs={1,1}) {
  CHECK(vu1Thread.GetObserverStatus(vu)==Status::released);
  CHECK(MTGS::GetObserverStatus(gs)==Status::released);
  CHECK(!s_observer_pine_drain.active() && pine_gate.enter());
}
void qt_pump(QEventLoop* m_event_loop) {
  while(s_observer_pine_drain.active()) {
    auto b=s_observer_cpu_boundary.enter();CHECK(b.valid());
#include "dispatch_step.inc"
    CHECK(false);
  }
}
