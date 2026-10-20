// Own fixture. All provider bodies are exact fragments from a private checkout.
#include "check.hpp"
#include "sh3_observer/worker_control.hpp"
#include "sh3_observer/cpu_boundary.hpp"
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
VMState GetState() { return vm_state.load(); }
GSVSyncMode GetEffectiveVSyncMode() { return GSVSyncMode::Off; }
bool ShouldAllowPresentThrottle() { return true; }
namespace Internal { bool IsObserverCpuThread(); bool CanRequestObserverWorker(); void BeforeObserverProducer(); }
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
struct GS_Packet { u32 offset, size, readAmount; };
struct Gif_Path {
  alignas(16) u8 buffer[256]{};
  std::atomic<unsigned> readAmount{0}, popped{0};
  GS_Packet packet{0, 16, 16};
  GS_Packet GetGSPacketMTVU() { return packet; }
  void PopGSPacketMTVU() { popped.fetch_add(1); }
  unsigned GetPendingGSPackets() { return 1 - popped.load(); }
};
struct { Gif_Path gifPath[3]; } gifUnit;
std::function<void()> on_vu_cancel;
struct {
  Threading::UserspaceSemaphore semaXGkick;
  void CancelObserverControl() { if (on_vu_cancel) on_vu_cancel(); }
} vu1Thread;
#include "gs_header.inc"
#include "gs_state.inc"
#include "packet_tag.inc"
#include "gs_control.inc"
struct PineDouble {
  bool active() const { return false; } bool effects_started() const { return false; }
  struct Result { unsigned id; }; Result status() const { return {}; }
  void cancel(unsigned) {} Result retire() { return {}; }
} s_observer_pine_drain;
PineDouble::Result s_observer_pine_result;
#include "stop_owner.inc"
#include "cpu_actor.inc"
#include "cpu_guard.inc"
#include "before_producer.inc"
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

template<class P> void until(P ready) {
  const auto end = std::chrono::steady_clock::now() + 5s;
  while (!ready()) { CHECK(std::chrono::steady_clock::now() < end); std::this_thread::yield(); }
}
void start(unsigned generation = 1) {
  CHECK(MTGS::WaitForOpen());
  const auto s = MTGS::GetObserverLifecycle(); CHECK(s.online && s.generation == generation);
}
void request(Token t = {1, 1}) {
  auto b = s_observer_cpu_boundary.enter(); CHECK(b.valid()); CHECK(MTGS::RequestObserverControl(t));
}
void held(Token t = {1, 1}) { until([&] { return MTGS::GetObserverStatus(t) == Status::held; }); }
void shutdown() {
  MTGS::ShutdownThread(); CHECK(!MTGS::GetObserverLifecycle().online);
  CHECK(!MTGS::s_thread.Joinable() && !MTGS::s_sem_event.WaitForEmpty());
}
void empty_wake() {
  start(); until([] { return MTGS::s_sem_event.m_state.load() == Threading::WorkSema::STATE_SLEEPING; });
  MTGS::s_CopyDataTally = 53; request(); held();
  CHECK(MTGS::s_CopyDataTally == 53); // Direct notification does not call SetEvent.
  CHECK(MTGS::s_mtx_RingBufferBusy2.try_lock()); MTGS::s_mtx_RingBufferBusy2.unlock();
  CHECK(MTGS::ReleaseObserverControl({1, 1})); shutdown();
}
void batch() {
  start(); freezeData data{}; MTGS::FreezeData freeze{&data, 0}; u8 fifo[16]{};
  MTGS::SendSimplePacket(MTGS::Command::Reset, 1, 0, 0);
  MTGS::SendSimplePacket(MTGS::Command::SoftReset, 3, 0, 0);
  MTGS::SendPointerPacket(MTGS::Command::Freeze, 1, &freeze);
  MTGS::SendPointerPacket(MTGS::Command::InitAndReadFIFO, 1, fifo);
  gifUnit.gifPath[1].readAmount.store(16);
  MTGS::SendSimplePacket(MTGS::Command::GSPacket, 0, 16, 1);
  gifUnit.gifPath[0].readAmount.store(32); vu1Thread.semaXGkick.Post();
  MTGS::SendSimplePacket(MTGS::Command::MTVUGSPacket, 0, 0, 0);
  MTGS::SendPointerPacket(MTGS::Command::AsyncCall, 0, new MTGS::AsyncCallType([] { callbacks.fetch_add(1); }));
  // Synthetic VSync payload with the layout consumed by the exact loop.
  const unsigned at = MTGS::s_WritePos.load(); auto& tag = reinterpret_cast<PacketTagType&>(MTGS::RingBuffer[at]);
  tag.command = static_cast<u32>(MTGS::Command::VSync); tag.data[0] = 17;
  for (unsigned i = 1; i <= 17; ++i) MTGS::RingBuffer[(at + i) & MTGS::RingBufferMask] = {};
  MTGS::s_QueuedFrameCount.store(1); MTGS::s_WritePos.store((at + 18) & MTGS::RingBufferMask);
  MTGS::s_SignalRingPosition.store(1000); MTGS::s_SignalRingEnable.store(true); MTGS::s_VsyncSignalListener.store(true);
  request(); held();
  CHECK(resets.load() == 1 && soft_resets.load() == 1 && callbacks.load() == 1 && vsyncs.load() == 1);
  CHECK(transfers.load() == 2 && freeze.retval == 9 && data.value == 41 && fifo[0] == 0x5a && fifo[15] == 0x5a);
  CHECK(gifUnit.gifPath[0].readAmount.load() == 0 && gifUnit.gifPath[0].popped.load() == 1 && gifUnit.gifPath[1].readAmount.load() == 0);
  CHECK(MTGS::s_ReadPos.load() == MTGS::s_WritePos.load() && MTGS::s_QueuedFrameCount.load() == 0);
  CHECK(!MTGS::s_SignalRingEnable.load() && !MTGS::s_VsyncSignalListener.load());
  CHECK(MTGS::s_sem_OnRingReset.posts.load() == 1 && MTGS::s_sem_Vsync.posts.load() == 1); shutdown();
}
void idle_boundary() {
  start(); block_idle.store(true);
  MTGS::RunOnGSThread([] { MTGS::SetRunIdle(true); }); idle_entered.acquire(); request();
  CHECK(MTGS::GetObserverStatus({1, 1}) == Status::pending); idle_go.release(); held();
  CHECK(presents.load() == 1 && throttles.load() == 1);
  std::this_thread::sleep_for(70ms); CHECK(presents.load() == 1 && throttles.load() == 1);
  CHECK(MTGS::s_mtx_RingBufferBusy2.try_lock()); MTGS::s_mtx_RingBufferBusy2.unlock();
  // Test-only flag injection makes cleanup deterministic without another blocked idle.
  MTGS::s_run_idle_flag.store(false); shutdown();
}
void stable_held() {
  start(); request(); held(); const auto read_before = MTGS::s_ReadPos.load();
  // Deliberately bypass the CPU producer guard through private packet writers.
  MTGS::SendPointerPacket(MTGS::Command::AsyncCall, 0, new MTGS::AsyncCallType([] { callbacks.fetch_add(1); }));
  MTGS::s_sem_event.NotifyOfWork(); std::this_thread::sleep_for(70ms);
  CHECK(MTGS::GetObserverStatus({1, 1}) == Status::held && callbacks.load() == 0 && MTGS::s_ReadPos.load() == read_before);
  CHECK(MTGS::ReleaseObserverControl({1, 1})); MTGS::WaitGS(false); CHECK(callbacks.load() == 1); shutdown();
}
void cancel_pending(bool timeout) {
  start(); std::binary_semaphore entered(0), go(0);
  MTGS::RunOnGSThread([&] { entered.release(); go.acquire(); callbacks.fetch_add(1); }); entered.acquire(); request();
  if (timeout) std::this_thread::sleep_for(60ms);
  CHECK(MTGS::GetObserverStatus({1, 1}) == Status::pending); CHECK(MTGS::ReleaseObserverControl({1, 1}));
  go.release(); MTGS::WaitGS(false); CHECK(callbacks.load() == 1 && MTGS::GetObserverStatus({1, 1}) == Status::released); shutdown();
}
void producer_release() {
  start(); request(); held();
  on_vu_cancel = [] { CHECK(MTGS::GetObserverStatus({1, 1}) == Status::released); };
  MTGS::RunOnGSThread([] { callbacks.fetch_add(1); }); on_vu_cancel = {};
  MTGS::WaitGS(false); CHECK(callbacks.load() == 1); shutdown();
}
void owner_release() {
  start(); request(); held();
  on_vu_cancel = [] { CHECK(MTGS::GetObserverStatus({1, 1}) == Status::released); };
  StopObserverPineDrain(); on_vu_cancel = {}; shutdown();
}
void close_held() { start(); request(); held(); MTGS::WaitForClose(); CHECK(!MTGS::GetObserverLifecycle().online && closed.load() == 1); shutdown(); }
void close_pending() {
  start(); std::binary_semaphore entered(0), go(0);
  MTGS::RunOnGSThread([&] { entered.release(); go.acquire(); callbacks.fetch_add(1); }); entered.acquire(); request();
  std::thread finisher([&] { until([] { return !MTGS::s_open_flag.load(); });
    CHECK(MTGS::GetObserverStatus({1, 1}) == Status::released); go.release(); });
  MTGS::WaitForClose(); finisher.join(); CHECK(callbacks.load() == 1 && closed.load() == 1); shutdown();
}
void shutdown_held() {
  start(); request(); held(); MTGS::s_open_flag.store(false); MTGS::s_sem_event.NotifyOfWork();
  std::this_thread::sleep_for(70ms);
  CHECK(MTGS::GetObserverStatus({1, 1}) == Status::held && closed.load() == 0);
  CHECK(MTGS::ReleaseObserverControl({1, 1})); shutdown(); CHECK(closed.load() == 1);
}
void reopen(bool restart_thread) {
  start(); request(); held(); MTGS::WaitForClose(); if (restart_thread) shutdown(); start(2);
  { auto b = s_observer_cpu_boundary.enter(); CHECK(b.valid()); CHECK(!MTGS::RequestObserverControl({1, 2})); }
  CHECK(!MTGS::ReleaseObserverControl({1, 1})); request({2, 1}); held({2, 1}); shutdown(); CHECK(opened.load() == 2 && closed.load() == 2);
}
void failed_open() {
  open_success.store(false); CHECK(!MTGS::WaitForOpen()); CHECK(!MTGS::GetObserverLifecycle().online);
  { auto b = s_observer_cpu_boundary.enter(); CHECK(b.valid()); CHECK(!MTGS::RequestObserverControl({1, 1})); }
  open_success.store(true); start(); request(); held(); shutdown(); CHECK(opened.load() == 1 && closed.load() == 1);
}
void opening() {
  block_open.store(true); MTGS::StartThread();
  // Test seam publishes the opening request without synchronously blocking CPU in WaitForOpen.
  MTGS::s_open_flag.store(true); MTGS::s_sem_event.NotifyOfWork(); open_entered.acquire();
  { auto b = s_observer_cpu_boundary.enter(); CHECK(b.valid()); CHECK(!MTGS::RequestObserverControl({1, 1})); }
  CHECK(!MTGS::GetObserverLifecycle().online); open_go.release(); MTGS::s_open_or_close_done.Wait();
  CHECK(MTGS::GetObserverLifecycle().generation == 1); request(); held(); shutdown();
}
void reject_actor() {
  start(); CHECK(!MTGS::RequestObserverControl({1, 1}));
  { auto b = s_observer_cpu_boundary.enter(); CHECK(b.valid()); vm_state.store(VMState::Running);
    CHECK(!MTGS::RequestObserverControl({1, 1})); vm_state.store(VMState::Paused);
    auto activity = s_observer_cpu_boundary.activity(); CHECK(!MTGS::RequestObserverControl({1, 1})); }
  request(); held();
  { auto b = s_observer_cpu_boundary.enter(); CHECK(b.valid()); CHECK(!MTGS::RequestObserverControl({1, 2})); }
  std::thread foreign([] { CHECK(!MTGS::RequestObserverControl({1, 2})); CHECK(!MTGS::ReleaseObserverControl({1, 1})); MTGS::CancelObserverControl(); });
  foreign.join(); CHECK(MTGS::GetObserverStatus({1, 1}) == Status::held); CHECK(!MTGS::ReleaseObserverControl({1, 2})); shutdown();
}
void mtvu_dependency() {
  start(); gifUnit.gifPath[0].readAmount.store(32);
  MTGS::SendSimplePacket(MTGS::Command::MTVUGSPacket, 0, 0, 0); request();
  CHECK(MTGS::GetObserverStatus({1, 1}) == Status::pending);
  vu1Thread.semaXGkick.Post(); held();
  CHECK(gifUnit.gifPath[0].popped.load() == 1 && gifUnit.gifPath[0].readAmount.load() == 0 && transfers.load() == 1); shutdown();
}
void signals_before_ack() {
  start(); std::binary_semaphore entered(0), go(0);
  MTGS::s_sem_OnRingReset.before_post = [&] { entered.release(); go.acquire(); };
  MTGS::s_SignalRingEnable.store(true); MTGS::s_SignalRingPosition.store(100);
  request(); entered.acquire(); CHECK(MTGS::GetObserverStatus({1, 1}) == Status::pending);
  go.release(); held(); CHECK(MTGS::s_sem_OnRingReset.posts.load() == 1 && MTGS::s_SignalRingPosition.load() == 0); shutdown();
}
void exhaustion() {
  MTGS::s_observer_generation = std::numeric_limits<std::uint32_t>::max(); CHECK(MTGS::WaitForOpen());
  CHECK(!MTGS::GetObserverLifecycle().online);
  { auto b = s_observer_cpu_boundary.enter(); CHECK(b.valid()); CHECK(!MTGS::RequestObserverControl({1, 1})); }
  MTGS::RunOnGSThread([] { callbacks.fetch_add(1); }); MTGS::WaitGS(false); CHECK(callbacks.load() == 1); shutdown();
}
void publication_gap(bool signals = false) {
  // Exact service on a test worker, forcing an earlier empty check before CPU publication.
  std::binary_semaphore checked(0), go(0), refused(0), finish(0); MTGS::s_open_flag.store(true);
  std::thread worker([&] {
    std::unique_lock lock(MTGS::s_mtx_RingBufferBusy2); CHECK(MTGS::StartObserverControl());
    CHECK(MTGS::s_ReadPos.load() == MTGS::s_WritePos.load()); checked.release(); go.acquire();
    MTGS::ServiceObserverControl(lock); CHECK(lock.owns_lock()); CHECK(MTGS::GetObserverStatus({1, 1}) == Status::pending);
    refused.release(); finish.acquire(); lock.unlock(); MTGS::StopObserverControl();
  });
  checked.acquire();
  if (signals) { MTGS::s_SignalRingEnable.store(true); MTGS::s_VsyncSignalListener.store(true); }
  else MTGS::SendSimplePacket(MTGS::Command::Reset, 0, 0, 0);
  request(); go.release(); refused.acquire();
  CHECK(resets.load() == 0); CHECK(MTGS::ReleaseObserverControl({1, 1})); finish.release(); worker.join(); MTGS::s_open_flag.store(false);
}
int main(int argc, char** argv) {
  CHECK(argc == 2); s_observer_cpu_thread = true; s_observer_cpu_boundary.set_online(true);
  const std::string_view name = argv[1];
  if (name == "empty_wake") empty_wake(); else if (name == "batch") batch();
  else if (name == "idle_boundary") idle_boundary(); else if (name == "stable_held") stable_held();
  else if (name == "cancel_pending") cancel_pending(false); else if (name == "timeout_pending") cancel_pending(true);
  else if (name == "producer_release") producer_release(); else if (name == "owner_release") owner_release();
  else if (name == "close_held") close_held(); else if (name == "close_pending") close_pending();
  else if (name == "shutdown_held") shutdown_held(); else if (name == "reopen") reopen(false);
  else if (name == "restart_thread") reopen(true); else if (name == "failed_open") failed_open();
  else if (name == "opening") opening(); else if (name == "reject_actor") reject_actor();
  else if (name == "mtvu_dependency") mtvu_dependency(); else if (name == "signals_before_ack") signals_before_ack();
  else if (name == "exhaustion") exhaustion(); else if (name == "publication_gap") publication_gap();
  else if (name == "signals_gap") publication_gap(true);
  else CHECK(false);
  s_observer_cpu_thread = false;
  std::printf("{\"result\":\"PASS\",\"case\":\"%s\"}\n", argv[1]);
}
