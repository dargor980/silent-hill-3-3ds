// Own fixtures; provider code is supplied only through private exact fragments.
#include "check.hpp"
#include "sh3_observer/worker_control.hpp"
#include "sh3_observer/cpu_boundary.hpp"
#include <atomic>
#include <cassert>
#include <chrono>
#include <cstdint>
#include <cstdio>
#include <cstring>
#include <limits>
#include <semaphore>
#include <string_view>
#include <thread>
#include <mach/mach.h>
#include <mach/mach_error.h>
#include <mach/semaphore.h>
#include <mach/task.h>

using u8 = std::uint8_t;
using u32 = std::uint32_t;
using u64 = std::uint64_t;
using s32 = std::int32_t;
using uptr = std::uintptr_t;
using Control = sh3::observer::WorkerControl;
using Token = Control::Token;
using Status = Control::Status;
using namespace std::chrono_literals;
#define pxAssert(value) CHECK(value)
#define pxAssertMsg(value, message) CHECK(value)
#define __fi
#define __ri
#define __cachelinesize 64
#define jNO_DEFAULT default: CHECK(false)
#define MTVU_LOG(...)
#define MTVU_ALWAYS_KICK 0
#define MTVU_SYNC_MODE 0
constexpr int _1mb = 1024 * 1024, _4kb = 4096;
constexpr int REG_TPC = 0, GIF_PATH_1 = 0;
constexpr int vu1RunCycles = 7;
std::atomic<unsigned> effects{0}, executions{0}, finished{0}, posts{0}, clears{0}, unpacked{0};
std::atomic_bool block_execute{false}, block_gs{false};
std::binary_semaphore execute_entered(0), execute_go(0), gs_entered(0), gs_space(0);

namespace Threading {
#include "kernel_class.inc"
#include "work_sema_class.inc"
using ThreadHandle = std::thread;
class Thread : public ThreadHandle {
public:
  bool Joinable() const { return joinable(); }
  void SetStackSize(unsigned) {}
  template<class F> void Start(F f) { ThreadHandle::operator=(std::thread(f)); }
  void Join() { join(); }
};
void SetNameOfCurrentThread(const char*) {}
class UserspaceSemaphore {
public:
  void Post() { CHECK(effects.load() == 2); posts.fetch_add(1); effects.store(3); }
};
}
#include "kernel_darwin.inc"
#include "check_for_work.inc"
#include "wait_for_work.inc"
#include "wait_for_empty.inc"
#include "kill.inc"
#include "reset.inc"

// Minimal effect/type doubles, intentionally not provider ABI or VU/GS emulation.
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
struct GifPathDouble {
  void FinishGSPacketMTVU() {
    CHECK(effects.load() == 1);
    if (block_gs.load()) { gs_entered.release(); gs_space.acquire(); }
    finished.fetch_add(1); effects.store(2);
  }
};
struct { GifPathDouble gifPath[1]; } gifUnit;
void MTVU_Unpack(void* data, VIFregisters& regs) {
  CHECK(*static_cast<u32*>(data) == 0x55667788 && regs.top == 29); unpacked.fetch_add(1);
}
static u32 size_u32(u32 x) { return (x + 3) >> 2; }
#include "commands.inc"

namespace VMManager {
constexpr unsigned EMU_THREAD_STACK_SIZE = 0;
namespace Internal {
bool IsObserverCpuThread();
bool CanRequestObserverWorker();
void BeforeObserverProducer();
}
}
// Test-only access to the exact class declaration; no provider statements replaced.
#define class struct
#define private public
#include "vu_class.inc"
#undef private
#undef class
extern VU_Thread vu1Thread;

enum class VMState { Paused, Running };
thread_local bool s_observer_cpu_thread = false;
thread_local sh3::observer::CpuBoundary s_observer_cpu_boundary;
thread_local VMState vm_state = VMState::Paused;
VMState GetState() { return vm_state; }
struct PineDouble {
  bool active() const { return false; }
  bool effects_started() const { return false; }
  struct Result { unsigned id; };
  Result status() const { return {}; }
  void cancel(unsigned) {}
  Result retire() { return {}; }
} s_observer_pine_drain;
PineDouble::Result s_observer_pine_result;
#include "stop_owner.inc"
#include "cpu_actor.inc"
#include "cpu_guard.inc"
#include "before_producer.inc"
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

template<class P> void until(P ready) {
  const auto end = std::chrono::steady_clock::now() + 5s;
  while (!ready()) { CHECK(std::chrono::steady_clock::now() < end); std::this_thread::yield(); }
}
void start(unsigned generation = 1) {
  vu1Thread.Open();
  until([&] { auto s = vu1Thread.GetObserverLifecycle(); return s.online && s.generation == generation; });
}
void held(Token token = {1, 1}) {
  until([&] { return vu1Thread.GetObserverStatus(token) == Status::held; });
}
void request(Token token = {1, 1}) {
  auto boundary = s_observer_cpu_boundary.enter(); CHECK(boundary.valid());
  CHECK(vu1Thread.RequestObserverControl(token));
}
void execute_packet() {
  vu1Thread.Write(MTVU_VU_EXECUTE); vu1Thread.Write(3); vu1Thread.Write(11);
  vu1Thread.Write(13); vu1Thread.Write(17); vu1Thread.CommitWritePos();
}
void check_completion() {
  CHECK(executions.load() == 1 && finished.load() == 1 && posts.load() == 1);
  CHECK(effects.load() == 3 && vu1Thread.vuCycles[0].load() == 47);
  CHECK(vu1Thread.GetReadPos() == vu1Thread.GetWritePos());
}
void close_offline() {
  vu1Thread.Close(); CHECK(!vu1Thread.GetObserverLifecycle().online);
  CHECK(!vu1Thread.semaEvent.WaitForEmpty());
}
void empty_wake() {
  start(); request(); held(); CHECK(vu1Thread.GetReadPos() == 0);
  CHECK(vu1Thread.ReleaseObserverControl({1, 1})); close_offline();
}
void command_batch() {
  start();
  const u32 payload = 0x12345678;
  vu1Thread.Write(MTVU_VU_WRITE_MICRO); vu1Thread.Write(8); vu1Thread.Write(4); vu1Thread.Write(payload);
  vu1Thread.Write(MTVU_VU_WRITE_DATA); vu1Thread.Write(12); vu1Thread.Write(4); vu1Thread.Write(payload);
  const u32 regs[8] = {101, 102, 103, 104, 105, 106, 107, 108};
  vu1Thread.Write(MTVU_VU_WRITE_VIREGS); vu1Thread.Write(regs, size_u32(32));
  vu1Thread.Write(MTVU_VU_WRITE_VFREGS); vu1Thread.Write(regs, size_u32(4 * 32));
  vu1Thread.Write(MTVU_VIF_WRITE_COL); vu1Thread.Write(regs, 16);
  vu1Thread.Write(MTVU_VIF_WRITE_ROW); vu1Thread.Write(regs + 4, 16);
  VIFregisters vr{1, 2, 3, 4, 23, 29};
  vu1Thread.Write(MTVU_VIF_UNPACK); vu1Thread.Write(regs, 16); vu1Thread.WriteRegs(&vr);
  vu1Thread.Write(4); vu1Thread.Write(0x55667788); execute_packet(); request(); held();
  check_completion();
  CHECK(clears.load() == 1 && unpacked.load() == 1);
  CHECK(std::memcmp(VU1.Micro + 8, &payload, 4) == 0 && std::memcmp(VU1.Mem + 12, &payload, 4) == 0);
  CHECK(VU1.VI[1].UL == 102 && std::memcmp(VU1.VF, regs, 32) == 0);
  CHECK(vu1Thread.vif.MaskCol[3] == 104 && vu1Thread.vif.MaskRow[3] == 108);
  CHECK(vu1Thread.vifRegs.top == 11 && vu1Thread.vifRegs.itop == 13 && vu1Thread.vuFBRST == 17);
  CHECK(vu1Thread.ReleaseObserverControl({1, 1})); close_offline();
}
void cancel_pending(bool timeout) {
  start(); block_execute.store(true); execute_packet(); vu1Thread.KickStart(); execute_entered.acquire();
  request(); CHECK(vu1Thread.GetObserverStatus({1, 1}) == Status::pending);
  if (timeout) std::this_thread::sleep_for(60ms);
  CHECK(vu1Thread.GetObserverStatus({1, 1}) == Status::pending);
  CHECK(vu1Thread.ReleaseObserverControl({1, 1})); execute_go.release();
  vu1Thread.WaitVU(); CHECK(vu1Thread.GetObserverStatus({1, 1}) == Status::released);
  check_completion(); close_offline();
}
void stable_held() {
  start(); execute_packet(); request(); held(); check_completion();
  const auto read_before = vu1Thread.GetReadPos();
  // Adversarial test injection via private raw writers, bypassing the CPU producer guard.
  execute_packet(); vu1Thread.semaEvent.NotifyOfWork();
  std::this_thread::sleep_for(70ms); // Longer than a local control wait; it must remain held.
  CHECK(vu1Thread.GetObserverStatus({1, 1}) == Status::held);
  CHECK(executions.load() == 1 && posts.load() == 1 && vu1Thread.GetReadPos() == read_before);
  CHECK(vu1Thread.ReleaseObserverControl({1, 1})); vu1Thread.WaitVU();
  CHECK(executions.load() == 2 && vu1Thread.GetReadPos() == vu1Thread.GetWritePos()); close_offline();
}
void producer_release() {
  start(); request(); held(); const u32 value = 313;
  vu1Thread.WriteDataMem(20, &value, sizeof(value)); // Exact producer guard precedes publication.
  CHECK(vu1Thread.GetObserverStatus({1, 1}) == Status::released);
  vu1Thread.WaitVU(); CHECK(std::memcmp(VU1.Mem + 20, &value, 4) == 0); close_offline();
}
void close_held() { start(); request(); held(); close_offline(); }
void shutdown_held() {
  start(); request(); held(); vu1Thread.m_shutdown_flag.store(true); vu1Thread.semaEvent.NotifyOfWork();
  std::this_thread::sleep_for(70ms);
  CHECK(vu1Thread.GetObserverStatus({1, 1}) == Status::held && vu1Thread.GetObserverLifecycle().online);
  CHECK(vu1Thread.ReleaseObserverControl({1, 1})); close_offline();
}
void close_pending() {
  start(); block_execute.store(true); execute_packet(); vu1Thread.KickStart(); execute_entered.acquire(); request();
  std::thread finisher([] { until([] { return vu1Thread.m_shutdown_flag.load(); });
    CHECK(vu1Thread.GetObserverStatus({1, 1}) == Status::released); execute_go.release(); });
  close_offline(); finisher.join(); check_completion();
}
void restart() {
  start(); request(); held(); close_offline(); vu1Thread.Reset(); start(2);
  { auto b = s_observer_cpu_boundary.enter(); CHECK(b.valid()); CHECK(!vu1Thread.RequestObserverControl({1, 2})); }
  CHECK(!vu1Thread.ReleaseObserverControl({1, 1})); request({2, 1}); held({2, 1}); close_offline();
}
void reject_actor() {
  start(); CHECK(!vu1Thread.RequestObserverControl({1, 1}));
  { auto b = s_observer_cpu_boundary.enter(); CHECK(b.valid()); vm_state = VMState::Running;
    CHECK(!vu1Thread.RequestObserverControl({1, 1})); vm_state = VMState::Paused;
    auto activity = s_observer_cpu_boundary.activity(); CHECK(!vu1Thread.RequestObserverControl({1, 1})); }
  request(); held();
  { auto b = s_observer_cpu_boundary.enter(); CHECK(b.valid()); CHECK(!vu1Thread.RequestObserverControl({1, 2})); }
  std::thread foreign([] { CHECK(!vu1Thread.RequestObserverControl({1, 2}));
    CHECK(!vu1Thread.ReleaseObserverControl({1, 1})); vu1Thread.CancelObserverControl(); });
  foreign.join(); CHECK(vu1Thread.GetObserverStatus({1, 1}) == Status::held);
  CHECK(!vu1Thread.ReleaseObserverControl({1, 2})); close_offline();
}
void full_gs_dependency() {
  start(); block_gs.store(true); execute_packet(); vu1Thread.KickStart(); gs_entered.acquire(); request();
  CHECK(vu1Thread.GetObserverStatus({1, 1}) == Status::pending && posts.load() == 0);
  std::thread consumer([] { gs_space.release(); }); consumer.join(); held(); check_completion(); close_offline();
}
void wrap() {
  start(); const int tail = VU_Thread::buffer_size - 1;
  vu1Thread.m_read_pos = tail; vu1Thread.m_ato_read_pos.store(tail);
  vu1Thread.m_write_pos = tail; vu1Thread.m_ato_write_pos.store(tail);
  const u32 value = 909; vu1Thread.WriteDataMem(24, &value, 4); request(); held();
  CHECK(vu1Thread.GetReadPos() == 4 && std::memcmp(VU1.Mem + 24, &value, 4) == 0); close_offline();
}
void exhaustion() {
  vu1Thread.m_observer_generation = std::numeric_limits<std::uint32_t>::max(); vu1Thread.Open();
  const u32 value = 19; vu1Thread.WriteDataMem(0, &value, 4); vu1Thread.WaitVU();
  CHECK(!vu1Thread.GetObserverLifecycle().online);
  { auto b = s_observer_cpu_boundary.enter(); CHECK(b.valid()); CHECK(!vu1Thread.RequestObserverControl({1, 1})); }
  CHECK(std::memcmp(VU1.Mem, &value, 4) == 0); close_offline();
}
void publication_gap() {
  // Deterministic unit seam: exact service method after an earlier empty check.
  // This case uses a test worker, not ExecuteRingBuffer; other cases run that body.
  std::binary_semaphore checked(0), go(0), refused(0), finish(0);
  std::thread worker([&] {
    CHECK(vu1Thread.StartObserverControl()); CHECK(vu1Thread.IsDone()); checked.release();
    go.acquire(); vu1Thread.ServiceObserverControl();
    CHECK(vu1Thread.GetObserverStatus({1, 1}) == Status::pending); refused.release();
    finish.acquire(); vu1Thread.StopObserverControl();
  });
  checked.acquire(); execute_packet(); request(); go.release(); refused.acquire();
  CHECK(vu1Thread.GetReadPos() != vu1Thread.GetWritePos() && executions.load() == 0);
  CHECK(vu1Thread.ReleaseObserverControl({1, 1})); finish.release(); worker.join();
  CHECK(!vu1Thread.GetObserverLifecycle().online);
}
int main(int argc, char** argv) {
  CHECK(argc == 2); s_observer_cpu_thread = true; s_observer_cpu_boundary.set_online(true);
  const std::string_view name = argv[1];
  if (name == "empty_wake") empty_wake();
  else if (name == "command_batch") command_batch();
  else if (name == "cancel_pending") cancel_pending(false);
  else if (name == "timeout_pending") cancel_pending(true);
  else if (name == "stable_held") stable_held();
  else if (name == "producer_release") producer_release();
  else if (name == "close_held") close_held();
  else if (name == "shutdown_held") shutdown_held();
  else if (name == "close_pending") close_pending();
  else if (name == "restart") restart();
  else if (name == "reject_actor") reject_actor();
  else if (name == "full_gs_dependency") full_gs_dependency();
  else if (name == "wrap") wrap();
  else if (name == "exhaustion") exhaustion();
  else if (name == "publication_gap") publication_gap();
  else CHECK(false);
  s_observer_cpu_thread = false;
  std::printf("{\"result\":\"PASS\",\"case\":\"%s\"}\n", argv[1]);
}
