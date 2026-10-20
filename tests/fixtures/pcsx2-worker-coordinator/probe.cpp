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
enum class VMState { Running, Paused };
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
struct { void Error(const char*) {} } Console;
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
sh3::observer::CooperativeGate pine_gate;
std::uint64_t host_generation=7, pine_generation=9;
namespace PINEServer {
auto BeginObserverExclusion(Clock::time_point d){return pine_gate.close(d);}
std::uint64_t GetObserverGeneration(){return pine_generation;}
}
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
  return s_observer_pine_drain.step(true,{host_generation,pine_generation});
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
void basic() {
  start();execute_packet();queue(std::uint64_t(1)<<40);wait_held();
  CHECK(executions==1 && finished==1 && vu1Thread.semaXGkick.posts==1);
  CHECK(vu1Thread.GetReadPos()==vu1Thread.GetWritePos());
  CHECK(MTGS::s_ReadPos==MTGS::s_WritePos);
  CHECK(MTGS::s_mtx_RingBufferBusy2.try_lock());MTGS::s_mtx_RingBufferBusy2.unlock();
  std::this_thread::sleep_for(60ms);CHECK(step()==State::held);
  {auto b=s_observer_cpu_boundary.enter();CHECK(s_observer_pine_drain.complete(true,{7,9}));}
  CHECK(s_observer_pine_drain.retire().state==State::completed);check_released();close_all();
}
void full_dependency() {
  start();std::binary_semaphore blocked(0),go(0);
  MTGS::RunOnGSThread([&]{blocked.release();go.acquire();});blocked.acquire();
  block_gs=true;execute_packet();vu1Thread.KickStart();gs_entered.acquire();
  // Raw injection fills every usable GS slot while its first callback is blocked.
  // The exact MainLoop consumes the ring. Its renderer and packet effects are doubles.
  const auto read=MTGS::s_ReadPos.load();
  while(((MTGS::s_WritePos.load()+3)&MTGS::RingBufferMask)!=read)
    MTGS::SendSimplePacket(MTGS::Command::Reset,1,0,0);
  const auto expected_resets=resets.load()+MTGS::RingBufferSize-4;
  MTGS::SendPointerPacket(MTGS::Command::AsyncCall,0,new MTGS::AsyncCallType([]{gs_space.release();}));
  gifUnit.gifPath[0].readAmount=16;
  MTGS::SendSimplePacket(MTGS::Command::MTVUGSPacket,0,0,0);
  CHECK(((MTGS::s_WritePos.load()+1)&MTGS::RingBufferMask)==read);
  MTGS::s_sem_event.NotifyOfWork();queue();CHECK(step()==State::draining);
  CHECK(vu1Thread.GetObserverStatus({1,1})==Status::pending);
  CHECK(MTGS::GetObserverStatus({1,1})==Status::invalid);
  go.release();wait_held();
  CHECK(resets==expected_resets && executions==1 && finished==1 && transfers==1);
  CHECK(gifUnit.gifPath[0].popped==1 && vu1Thread.semaXGkick.posts==1);
  CHECK(MTGS::s_ReadPos==MTGS::s_WritePos);
  CHECK(VMManager::Internal::CancelObserverPineDrain(1));StopObserverPineDrain();check_released();close_all();
}
std::binary_semaphore blocked_gs(0),continue_gs(0);
void block_phase(int phase,std::chrono::milliseconds timeout=2000ms) {
  if(phase==1){block_execute=true;execute_packet();vu1Thread.KickStart();execute_entered.acquire();}
  else if(phase==2){MTGS::RunOnGSThread([]{blocked_gs.release();continue_gs.acquire();callbacks++;});blocked_gs.acquire();}
  queue(1,timeout);CHECK(step()==State::draining);
  if(phase==2)until([]{return step()==State::draining && MTGS::GetObserverStatus({1,1})==Status::pending;});
  if(phase==3)wait_held();
}
void unblock(int phase) {if(phase==1)execute_go.release();if(phase==2)continue_gs.release();}
void abort_phase(int phase,bool timeout,bool epoch) {
  start();block_phase(phase,timeout?100ms:2000ms);
  if(timeout){std::this_thread::sleep_for(110ms);CHECK(step()==State::timed_out);}
  else if(epoch){++host_generation;CHECK(step()==State::invalidated);}
  else CHECK(VMManager::Internal::CancelObserverPineDrain(1));
  CHECK(!pine_gate.enter());StopObserverPineDrain();
  CHECK(s_observer_pine_result.state==(timeout?State::timed_out:epoch?State::invalidated:State::cancelled));
  CHECK(vu1Thread.GetObserverStatus({1,1})==Status::released);
  if(phase>1)CHECK(MTGS::GetObserverStatus({1,1})==Status::released);
  unblock(phase);vu1Thread.WaitVU();MTGS::WaitGS(false);close_all();
}
void producer() {
  start();queue();wait_held();const u32 value=751;
  vu1Thread.WriteDataMem(24,&value,4);check_released();
  CHECK(s_observer_pine_result.state==State::cancelled);
  vu1Thread.WaitVU();CHECK(std::memcmp(VU1.Mem+24,&value,4)==0);close_all();
}
void close_pending(int phase) {
  start();block_phase(phase);
  std::thread finisher([&]{
    if(phase==1)until([]{return vu1Thread.m_shutdown_flag.load();});
    else until([]{return !MTGS::s_open_flag.load();});
    CHECK(vu1Thread.GetObserverStatus({1,1})==Status::released);
    if(phase>1)CHECK(MTGS::GetObserverStatus({1,1})==Status::released);
    unblock(phase);
  });
  if(phase==1)vu1Thread.Close();else MTGS::WaitForClose();
  finisher.join();CHECK(s_observer_pine_result.state==State::cancelled);close_all();
}
void restart() {
  start();queue();wait_held();close_all();vu1Thread.Reset();start(2);queue(2);wait_held();
  CHECK(vu1Thread.GetObserverStatus({2,2})==Status::held && MTGS::GetObserverStatus({2,2})==Status::held);
  CHECK(vu1Thread.GetObserverStatus({1,1})==Status::invalid);close_all();
}
void offline(bool failed) {
  if(failed){open_success=false;CHECK(!MTGS::WaitForOpen());}
  else CHECK(MTGS::WaitForOpen());
  queue();CHECK(step()==State::rejected);StopObserverPineDrain();
  CHECK(s_observer_pine_result.state==State::rejected && pine_gate.enter());close_all();
}
void qt_pump(QEventLoop* m_event_loop) {
  while(s_observer_pine_drain.active()) {
    auto b=s_observer_cpu_boundary.enter();CHECK(b.valid());
#include "dispatch_step.inc"
    CHECK(false);
  }
}
void qt_dispatch(bool pine_wait,bool timeout) {
  start();QEventLoop loop;QObject receiver;bool called=false;
  auto payload=std::make_shared<int>(93);std::weak_ptr<int> weak=payload;
  auto prior=pine_wait?pine_gate.enter():sh3::observer::CooperativeGate::Work{};
  CHECK(QMetaObject::invokeMethod(&receiver,[payload,&called,pine_wait]{
    CHECK(*payload==93);called=true;
    if(!pine_wait){CHECK(!s_observer_pine_drain.active());CHECK(pine_gate.enter());}
    else CHECK(s_observer_pine_drain.active() && !s_observer_pine_drain.effects_started());
  },Qt::QueuedConnection));payload.reset();
  if(pine_wait)QTimer::singleShot(0,&receiver,[&]{prior={};});
  if(timeout)block_phase(1,100ms);else queue();
  qt_pump(&loop);
  CHECK(s_observer_pine_result.state==(timeout?State::timed_out:State::completed));
  CHECK(called==pine_wait);
  if(!pine_wait){CHECK(!weak.expired());VMManager::Internal::BeforeObserverProducer();auto a=VMManager::Internal::EnterObserverCpuActivity();loop.processEvents();}
  CHECK(called && weak.expired());if(timeout)execute_go.release();vu1Thread.WaitVU();close_all();
}
int main(int argc,char** argv) {
  QCoreApplication app(argc,argv);CHECK(argc==2);std::string name=argv[1];
  s_observer_cpu_thread=true;s_observer_cpu_boundary.set_online(true);
  if(name=="basic")basic();else if(name=="full_dependency")full_dependency();
  else if(name=="producer")producer();else if(name=="restart")restart();
  else if(name=="offline")offline(false);else if(name=="failed_open")offline(true);
  else if(name=="close_vu")close_pending(1);else if(name=="close_gs")close_pending(2);
  else if(name=="qt_dispatch")qt_dispatch(false,false);else if(name=="qt_pine")qt_dispatch(true,false);
  else if(name=="qt_timeout")qt_dispatch(false,true);
  else if(name.starts_with("cancel_"))abort_phase(name.back()-'0',false,false);
  else if(name.starts_with("timeout_"))abort_phase(name.back()-'0',true,false);
  else if(name.starts_with("epoch_"))abort_phase(name.back()-'0',false,true);
  else CHECK(false);
  std::printf("{\"result\":\"PASS\",\"case\":\"%s\"}\n",argv[1]);
}
