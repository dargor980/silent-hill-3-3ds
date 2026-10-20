// Own orchestration and doubles. Provider bodies live only in private *.inc files.
#include "check.hpp"
#include "sh3_observer/retained_drain.hpp"
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
unsigned effects{}, phase{}, cases{}, locale_cases{};
std::uint64_t digest = 1469598103934665603ULL, next_id{};
void hash(u32 value) {
  for (unsigned i=0;i<4;++i) { digest ^= (value >> (i*8)) & 255; digest *= 1099511628211ULL; }
}
void effect(u32 kind) {
#ifdef SH3_ENABLE_OBSERVER
  if (phase>=2) { CHECK(!s_observer_pine_drain.active()); CHECK(port.releases==1); CHECK(source.gate.enter()); }
#endif
  ++effects; hash(kind);
}
CooperativeGate::Work prior;
void start(unsigned p) {
  CHECK(!s_observer_pine_drain.active()); CHECK(source.gate.enter());
  phase=p; effects=0; port.releases=0; at_release=[&] { CHECK(effects==0); };
  port.progress=p==3 ? Progress::held : p==4 ? Progress::rejected : Progress::pending;
  if (p==0) return;
  if (p==1) prior=source.gate.enter();
  CHECK(s_observer_pine_drain.submit({++next_id,{1,1},Clock::now()+std::chrono::seconds(5)}));
  auto b=cpu.enter(); auto s=s_observer_pine_drain.step(true,{1,1});
  CHECK(s==(p==3 ? State::held : p==4 ? State::rejected : State::draining));
}
void finish() {
#ifdef SH3_ENABLE_OBSERVER
  if (phase>=2) { CHECK(port.releases==1); CHECK(!s_observer_pine_drain.active());
    CHECK(s_observer_pine_result.state==(phase==4 ? State::rejected : State::cancelled)); }
  if (phase==1) { CHECK(s_observer_pine_drain.active()); CHECK(port.releases==0); CHECK(!source.gate.enter()); }
#endif
  at_release={}; prior={};
  if (s_observer_pine_drain.active()) {
    s_observer_pine_drain.cancel(next_id); s_observer_pine_drain.retire();
  }
  CHECK(source.gate.enter()); ++cases;
}
#define pxAssertRel(x, ...) CHECK(x)
#define pxAssertMsg(x, ...) CHECK(x)
#define MTVU_LOG(...) do {} while (0)
enum class GSHardwareDownloadMode { Enabled, Unsynchronized, Disabled };
struct { struct { GSHardwareDownloadMode HWDownloadMode{}; } GS; struct {u32 EECycleSkip{2};} Speedhacks; } EmuConfig;
bool hardware=true;
bool GSIsHardwareRenderer() { return hardware; }
struct {struct {std::uint64_t _u64{};} BITBLTBUF,TRXPOS,TRXREG;} vif1;
void GSReadLocalMemoryUnsync(u8* p,u32 n,std::uint64_t,std::uint64_t,std::uint64_t) {
  effect(1); std::memset(p,0x31,n*16);
}
using GIF_PATH = unsigned;
struct GS_Packet {u32 offset{},size{},readAmount{};};
struct Path {std::atomic<u32> readAmount{}; alignas(16) u8 buffer[128]{};};
struct {
  Path gifPath[3];
  void TransferGSPacketData(unsigned,const void*,unsigned) {effect(15);}
} gifUnit;
bool COPY_GS_PACKET_TO_MTGS=false;
struct Packet {unsigned kind;u32 first,second,path;void* pointer;};
std::vector<Packet> packets;
enum class FreezeAction { Load, Save };
namespace MTGS {
using AsyncCallType=std::function<void()>;
enum class Command { InitAndReadFIFO, AsyncCall, Freeze, GSPacket, MTVVUnused, MTVUGSPacket };
struct FreezeData {int retval{};};
struct {u128 m_Ring[32];} RingBuffer;
unsigned s_packet_writepos{},RingBufferSize=32;
bool open=true;
bool IsOpen() {return open;}
void SendPointerPacket(Command c,u32 n,void* p) {effect(2);packets.push_back({unsigned(c),n,0,0,p});}
void SetEvent() {effect(3);}
void RunOnGSThread(AsyncCallType);
void InitAndReadFIFO(u8*,u32);
void Freeze(FreezeAction,FreezeData&);
bool SaveMemorySnapshot(u32,u32,bool,bool,u32*,u32*,std::vector<u32>*);
void SendSimpleGSPacket(Command c,u32 offset,u32 size,GIF_PATH path) {
  effect(4); packets.push_back({unsigned(c),offset,size,path,nullptr});
  hash(offset); hash(size); hash(path);
}
void PrepDataPacket(GIF_PATH path,u32 size) {effect(5);hash(path);hash(size);}
void SendDataPacket() {effect(6);}
void Consume() {
  auto batch=std::move(packets); packets.clear();
  for (auto p:batch) {
    if (p.kind==unsigned(Command::AsyncCall)) {
      std::unique_ptr<AsyncCallType> f(static_cast<AsyncCallType*>(p.pointer)); (*f)();
    } else if (p.kind==unsigned(Command::InitAndReadFIFO)) {
      std::memset(p.pointer,0x51,p.first*16);
    } else if (p.kind==unsigned(Command::Freeze)) {
      static_cast<FreezeData*>(p.pointer)->retval=73;
    }
  }
}
void WaitGS(bool =true,bool =false,bool =false) {effect(7);Consume();}
}
void MemCopy_WrappedDest(const u128* src,u128* dest,unsigned,unsigned,unsigned count) {
  effect(8);std::memcpy(dest,src,count*16);
}
bool snapshot_result=true;
bool GSSaveSnapshotToMemory(u32 w,u32 h,bool aspect,bool crop,u32* width,u32* height,std::vector<u32>* pixels) {
  effect(9);CHECK(aspect && !crop);*width=w;*height=h;pixels->assign({13,17});return snapshot_result;
}
#include "fifo.inc"
#include "async.inc"
#include "freeze.inc"
#include "snapshot.inc"
#include "blank.inc"
#include "completed.inc"
#include "mtvu-packet.inc"
struct REG_VI {u8 values[64];};
struct VECTOR {u8 values[128];};
struct VIFregisters {u32 data[4];};
using VIFregistersMTVU=VIFregisters;
struct vifStruct {u32 tag[4], StructEnd, MaskCol[4], MaskRow[4];};
static u32 size_u32(u32 n) {return (n+3)>>2;}
enum {MTVU_VU_EXECUTE,MTVU_VU_WRITE_MICRO,MTVU_VU_WRITE_DATA,MTVU_VU_WRITE_VIREGS,
MTVU_VU_WRITE_VFREGS,MTVU_VIF_WRITE_COL,MTVU_VIF_WRITE_ROW,MTVU_VIF_UNPACK};
constexpr unsigned GIF_TRANS_MTVU=1,REG_VPU_STAT=0,VU_MTVU_BUSY=1;
bool INSTANT_VU1=false;
struct {u32 cycle{};} cpuRegs;
struct {u32 cycle{};struct {u32 UL{};} VI[1];} VU0;
void CPU_INT(unsigned irq,u32 cycles) {effect(16);hash(irq);hash(cycles);}
std::vector<u32> words;
std::vector<u8> payload;
unsigned reserve{};
struct VU_Thread {
  struct {void WaitForEmpty() {effect(17);}} semaEvent;
  void ReserveSpace(unsigned n) {effect(10);reserve=n;}
  void Write(u32 n) {effect(11);words.push_back(n);hash(n);}
  void Write(const void* p,u32 n) {
    effect(12);auto* b=static_cast<const u8*>(p);payload.insert(payload.end(),b,b+n);
    for (unsigned i=0;i<n;++i) hash(b[i]);
  }
  void WriteRegs(VIFregisters* p) {Write(p,sizeof(*p));}
  void CommitWritePos() {effect(13);}
  void KickStart() {effect(14);}
  void Get_MTVUChanges() {effect(18);}
  u32 Get_vuCycles() {return 8;}
  void WaitVU();
  void ExecuteVU(u32,u32,u32,u32);
  void VifUnpack(vifStruct&,VIFregisters&,const u8*,u32);
  void WriteMicroMem(u32,const void*,u32);
  void WriteDataMem(u32,const void*,u32);
  void WriteVIRegs(REG_VI*);
  void WriteVFRegs(VECTOR*);
  void WriteCol(vifStruct&);
  void WriteRow(vifStruct&);
} vu;
#include "execute.inc"
#include "unpack.inc"
#include "micro.inc"
#include "data.inc"
#include "vi.inc"
#include "vf.inc"
#include "col.inc"
#include "row.inc"
#include "wait-vu.inc"
// Real dispatch/slot bodies; transport is a deterministic queue, not Qt.
std::vector<std::function<void()>> cpu_queue;
struct EmuThread {bool isOnEmuThread() {return s_observer_cpu_thread;} void runOnCPUThread(const std::function<void()>&);};
EmuThread emu;
EmuThread* g_emu_thread=&emu;
namespace Qt {enum Connection {QueuedConnection,BlockingQueuedConnection};}
#define Q_ARG(type, value) value
struct QMetaObject {
  static void invokeMethod(EmuThread* target,const char*,Qt::Connection type,std::function<void()> f) {
    CHECK(target==&emu && type==Qt::QueuedConnection);
    cpu_queue.push_back([target,f=std::move(f)] {target->runOnCPUThread(f);});
  }
};
namespace Host {void RunOnCPUThread(std::function<void()>,bool=false);}
namespace FullscreenUI {
bool initialized=true;
unsigned changed{};
bool IsInitialized() {return initialized;}
void LocaleChanged() {effect(19);++changed;}
}
#include "qt-slot.inc"
#include "qt-dispatch.inc"
void LocaleRequest() {
#include "locale.inc"
}
void dispatchCPU() {
  auto work=std::move(cpu_queue); cpu_queue.clear();
  for (auto& f:work) f();
}
void operations() {
  std::array<u8,32> destination;
  std::array<u8,16> input;input.fill(37);
  vifStruct vif{}; VIFregisters regs{}; REG_VI vi{}; VECTOR vf{};
  std::memset(&vif,5,sizeof(vif));std::memset(&regs,7,sizeof(regs));
  std::memset(&vi,9,sizeof(vi));std::memset(&vf,11,sizeof(vf));
  for (unsigned op=0;op<22;++op) for (unsigned p=0;p<5;++p) {
    CHECK(packets.empty()); words.clear();payload.clear();reserve=0;
    destination.fill(0x75);gifUnit.gifPath[1].readAmount=0;
    std::memset(gifUnit.gifPath[1].buffer,0x19,128);
    start(p);
    at_release=[&] {CHECK(effects==0);CHECK(gifUnit.gifPath[1].readAmount==0);
      CHECK(std::all_of(destination.begin(),destination.end(),[](u8 v){return v==0x75;}));};
    if (op<4) {
      hardware=op!=3;
      EmuConfig.GS.HWDownloadMode=op==0||op==3 ? GSHardwareDownloadMode::Unsynchronized : op==1 ? GSHardwareDownloadMode::Disabled : GSHardwareDownloadMode::Enabled;
      MTGS::InitAndReadFIFO(destination.data(),2);
      const u8 expected=op==0 ? 0x31 : op==1 ? 0 : 0x51;
      CHECK(std::all_of(destination.begin(),destination.end(),[&](u8 v){return v==expected;}));
      for(auto b:destination)hash(b);
    } else if (op==4) {
      Gif_AddBlankGSPacket(48,1); CHECK(gifUnit.gifPath[1].readAmount==48);
      CHECK(packets.size()==1 && packets[0].first==~0u && packets[0].second==48);
    } else if (op==5 || op==6) {
      COPY_GS_PACKET_TO_MTGS=op==6;GS_Packet packet{16,32,0};Gif_AddCompletedGSPacket(packet,1);
      CHECK(gifUnit.gifPath[1].readAmount==(op==5 ? 32u:0u));
      if (op==6) CHECK(std::memcmp(MTGS::RingBuffer.m_Ring,gifUnit.gifPath[1].buffer+16,32)==0);
      else CHECK(packets.size()==1 && packets[0].first==16 && packets[0].second==32);
    } else if (op==7) {
      GS_Packet packet{};Gif_AddGSPacketMTVU(packet,1);
      CHECK(packets.size()==1 && packets[0].kind==unsigned(MTGS::Command::MTVUGSPacket));
    } else if (op==8) {
      auto value=std::make_shared<unsigned>(83);std::weak_ptr<unsigned> weak=value;unsigned called=0;
      MTGS::RunOnGSThread([value,&called]{effect(20);CHECK(*value==83);++called;});
      value.reset();CHECK(!weak.expired() && called==0);MTGS::Consume();CHECK(weak.expired() && called==1);
    } else if (op==9 || op==10) {
      MTGS::FreezeData d{};MTGS::Freeze(op==9 ? FreezeAction::Load:FreezeAction::Save,d);CHECK(d.retval==73);
    } else if (op==11 || op==12) {
      snapshot_result=op==11;u32 w{},h{};std::vector<u32> pixels;
      CHECK(MTGS::SaveMemorySnapshot(12,8,true,false,&w,&h,&pixels)==snapshot_result);
      CHECK(w==12 && h==8 && pixels==std::vector<u32>({13,17}));
    } else if (op==13) {
      cpuRegs.cycle=VU0.cycle=0;VU0.VI[0].UL=0;vu.ExecuteVU(3,4,5,6);
      CHECK(words==std::vector<u32>({MTVU_VU_EXECUTE,3,4,5,6}));CHECK(reserve==5);
      CHECK(cpuRegs.cycle==16 && VU0.cycle==16 && VU0.VI[0].UL==0x100);
    } else if (op==14) {
      vu.VifUnpack(vif,regs,input.data(),input.size());
      CHECK(words==std::vector<u32>({MTVU_VIF_UNPACK,16}));CHECK(reserve==14);
      CHECK(payload.size()==48 && std::equal(input.begin(),input.end(),payload.end()-16));
    } else if (op==15 || op==16) {
      if(op==15)vu.WriteMicroMem(2,input.data(),input.size());else vu.WriteDataMem(2,input.data(),input.size());
      CHECK(words==std::vector<u32>({op==15 ? MTVU_VU_WRITE_MICRO:MTVU_VU_WRITE_DATA,2,16}));
      CHECK(reserve==7 && payload==std::vector<u8>(input.begin(),input.end()));
    } else if (op==17) {vu.WriteVIRegs(&vi);CHECK(reserve==9 && payload==std::vector<u8>(8,9));}
    else if (op==18) {vu.WriteVFRegs(&vf);CHECK(reserve==33 && payload==std::vector<u8>(32,11));}
    else if (op==19) {vu.WriteCol(vif);CHECK(reserve==5 && payload==std::vector<u8>(16,5));}
    else if (op==20) {vu.WriteRow(vif);CHECK(reserve==5 && payload==std::vector<u8>(16,5));}
    else {vu.WaitVU();}
    MTGS::Consume();finish();
  }
}
void locale() {
  for (unsigned variant=0;variant<6;++variant) {
    g_emu_thread=variant==0 ? nullptr:&emu;MTGS::open=true;FullscreenUI::initialized=true;FullscreenUI::changed=0;
    // New route also works with delayed UI initialization and CPU re-entry.
    if(variant==4)FullscreenUI::initialized=false;
    start(variant==5 ? 3:0);s_observer_cpu_thread=false;
    LocaleRequest();CHECK(FullscreenUI::changed==0);
#ifndef PROVIDER_BASELINE
    CHECK(packets.empty());CHECK(cpu_queue.size()==(variant==0 ? 0u:1u));
    if(variant==1)MTGS::open=false;
    s_observer_cpu_thread=true;dispatchCPU();
    CHECK(packets.size()==(variant==0||variant==1 ? 0u:1u));
    if(variant==2)FullscreenUI::initialized=false;
    if(variant==4)FullscreenUI::initialized=true;
    MTGS::Consume();CHECK(FullscreenUI::changed==(variant>=3 ? 1u:0u));
#else
    // Historical route: direct UI publication; deliberately different semantics.
    CHECK(cpu_queue.empty());s_observer_cpu_thread=true;MTGS::Consume();
    CHECK(FullscreenUI::changed==(variant==4 ? 0u:1u));
#endif
    finish();++locale_cases;
  }
  g_emu_thread=&emu;MTGS::open=true;FullscreenUI::initialized=true;
}
int main() {
  cpu.set_online(true);s_observer_cpu_thread=true;
  operations();const auto common_digest=digest;CHECK(cases==110);
  locale();
  unsigned thread_cases=0;
#ifdef SH3_ENABLE_OBSERVER
  start(3);
  std::thread other([] {CHECK(!s_observer_cpu_thread);VMManager::Internal::BeforeObserverProducer();});other.join();
  CHECK(s_observer_pine_drain.status().state==State::held && port.releases==0);
  VMManager::Internal::BeforeObserverProducer();finish();++thread_cases;
#endif
  std::cout << "{\"result\":\"PASS\",\"common_cases\":110,\"locale_cases\":" << locale_cases
            << ",\"thread_cases\":" << thread_cases << ",\"effects_digest\":\"" << std::hex << common_digest << "\"}\n";
}
