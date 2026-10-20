// Own synthetic harness. The generated *.inc files remain in the private stage.
// Provider bodies are copied verbatim; address resolution, registers, logging,
// interrupt delivery and GS scheduling below are explicitly test doubles.
#include "check.hpp"
#include "sh3_observer/capture.hpp"
#include "sh3_observer/physical_writes.hpp"
#include <algorithm>
#include <array>
#include <cstdint>
#include <cstdio>
#include <cstring>
#include <string>
#include <vector>
using namespace sh3::observer;
using u8=std::uint8_t; using u32=std::uint32_t; using s32=std::int32_t; using uint=unsigned;
struct alignas(16) u128 { std::array<u8,16> bytes; };
using tDMA_TAG=u128;
#define __ri
#define __fi
#define SIF_LOG(...) ((void)0)
#define SPR_LOG(...) ((void)0)
#define pxAssert(x) CHECK(x)
#define pxAssertMsg(x, ...) CHECK(x)
unsigned bus_errors=0, interrupts=0;
#define pxFail(...) (++bus_errors)
#define CPU_INT(...) (++interrupts)
struct Logger { template<class... T> void Warning(T...) {} template<class... T> void WriteLn(T...) {} } DevCon,Console;
struct { std::uint64_t cycle=1001; } cpuRegs;
constexpr unsigned _16kb=16384;
alignas(4096) std::array<u8,ram_size> ram;
alignas(4096) std::array<u8,4096> other;
std::array<u128,1024> scratch;
std::array<u128,128> payload;
#define psSu128(a) scratch[(a)/16]
struct Event {std::uintptr_t address; std::size_t size;};
std::vector<Event> events;
unsigned copies=0, zero_copies=0, unknowns=0, cases=0;
bool check_callbacks=true, observing=true;
LifetimeGuard* current_guard=nullptr;
std::uint64_t digest=14695981039346656037ULL;
void hash(std::uint64_t v) {for(unsigned i=0;i<8;++i){digest^=(v>>(i*8))&255;digest*=1099511628211ULL;}}
namespace sh3::observer {
void harness_write(std::uint64_t a,std::uint64_t n,std::uint64_t c) noexcept {
  CHECK(n>0); CHECK(c==1001); events.push_back({static_cast<std::uintptr_t>(a),static_cast<std::size_t>(n)});
  before_host_write(a,n,c);
}
void harness_unknown(std::uint64_t c) noexcept {++unknowns;before_untracked_write(c);}
}
void* checked_memcpy(void* dst,const void* src,std::size_t n) {
  if(n==0){++zero_copies;return dst;}
#ifdef SH3_ENABLE_OBSERVER
  if(check_callbacks){CHECK(events.size()==copies+1);CHECK(events.back().address==reinterpret_cast<std::uintptr_t>(dst));CHECK(events.back().size==n);}
  if(check_callbacks && observing) {
    const auto address=reinterpret_cast<std::uintptr_t>(dst);
    const auto base=reinterpret_cast<std::uintptr_t>(ram.data());
    for(const auto& range:std::array<std::array<unsigned,2>,6>{{{0x1000,4},{0x2000,24},{0x3000,32},{0x3024,8},{0x4000,12},{0,0}}})
      if(range[1] && address<base+range[0]+range[1] && base+range[0]<address+n)
        CHECK(current_guard->report().reason==LifetimeReason::protected_write);
  }
#endif
  ++copies;
  return std::memcpy(dst,src,n);
}
struct {struct{u32 ADDR=0;} rbor,stadr;struct{u32 RMSK=0;} rbsr;struct{int STS=0;} ctrl;struct{bool BEIS=false;} stat;} dmacRegs;
bool mapped=true;
u8* resolved=nullptr;
void* PSM(u32 a) {return mapped?ram.data()+a:nullptr;}
tDMA_TAG* dmaGetAddr(u32,bool){return reinterpret_cast<tDMA_TAG*>(resolved);}
struct Channel {
  u32 madr=0x5000,qwc=0;
  struct{int MOD=0;u32 TAG=0;} chcr;
  tDMA_TAG* getAddr(u32,int,bool){return reinterpret_cast<tDMA_TAG*>(resolved);}
} sif0ch,sif2dma,vif1ch;
constexpr int DMAC_SIF0=5,DMAC_SIF2=7,STS_SIF0=1,NORMAL_MODE=0,TAG_CNTS=1;
constexpr int FIFO_SIF_W=128;
#define before_host_write harness_write
#define before_untracked_write harness_unknown
#define memcpy checked_memcpy
#include "spr.inc"
#include "wrapped.inc"
#include "mfifo.inc"
struct SifFifo {
  u32 data[FIFO_SIF_W]{};int readPos=0,size=0;
#include "sif-read.inc"
};
struct Sif {SifFifo fifo;struct{int cycles=0;} ee;} sif0,sif2;
namespace s0 {
#include "sif0.inc"
}
namespace s2 {
#include "sif2.inc"
}
struct {struct{unsigned OFC=0;} ctrl;} ipuRegs;
struct IPU_Fifo_Output {u32 data[32]{};int readpos=0;void read(void*,uint);};
#include "ipu.inc"
#undef memcpy
struct{u32 GSLastDownloadSize=0;bool done=false;} vif1;
struct{struct{u32 FQC=0;} stat;} vif1Regs;
unsigned g_vif1Cycles=0,gs_calls=0;
bool defer_gs=false;
u8* queued_dst=nullptr;u32 queued_size=0;
namespace MTGS {
void InitAndReadFIFO(u8* mem,u32 qwc) {
  ++gs_calls;
#ifdef SH3_ENABLE_OBSERVER
  if(qwc && observing){CHECK(unknowns==1);CHECK(current_guard->report().reason==LifetimeReason::lost);}
#endif
  if(defer_gs){queued_dst=mem;queued_size=qwc;}
  else std::memset(mem,0x5a,qwc*16);
}
}
#include "vif.inc"
#undef before_host_write
#undef before_untracked_write
LifetimePlan plan(){return {{{{1}},7,100,1000},{0x1000,0x2000,0x3000,0x4000},1000};}
template<class F> void run(F test,bool bind=true) {
  std::fill_n(ram.begin(),0x10000,0xa5);other.fill(0xa5);
  auto* bytes=reinterpret_cast<u8*>(scratch.data());for(unsigned i=0;i<16384;++i)bytes[i]=static_cast<u8>(i*13+7);
  bytes=reinterpret_cast<u8*>(payload.data());for(unsigned i=0;i<sizeof(payload);++i)bytes[i]=static_cast<u8>(i*3+19);
  events.clear();copies=zero_copies=unknowns=bus_errors=interrupts=gs_calls=0;check_callbacks=true;observing=bind;
  mapped=true;resolved=ram.data()+0x5000;dmacRegs={};sif0ch={};sif2dma={};vif1ch={};sif0={};sif2={};ipuRegs={};vif1={};vif1Regs={};g_vif1Cycles=0;defer_gs=false;queued_dst=nullptr;queued_size=0;
  LifetimeGuard guard;CHECK(guard.arm(plan()));current_guard=&guard;PhysicalWrites bridge(guard,reinterpret_cast<std::uintptr_t>(ram.data()));
  if(bind){WriteBinding binding(bridge);CHECK(binding.connected());test(guard);}else test(guard);
  for(unsigned i=0;i<0x6000;++i)hash(ram[i]);for(auto b:other)hash(b);
  hash(copies);hash(zero_copies);hash(bus_errors);hash(interrupts);hash(gs_calls);
  hash(sif0ch.madr);hash(sif0ch.qwc);hash(sif0.fifo.size);hash(sif0.fifo.readPos);hash(sif0.ee.cycles);
  hash(sif2dma.madr);hash(sif2dma.qwc);hash(sif2.fifo.size);hash(sif2.fifo.readPos);hash(sif2.ee.cycles);
  hash(vif1ch.madr);hash(vif1ch.qwc);hash(vif1.GSLastDownloadSize);hash(vif1Regs.stat.FQC);hash(g_vif1Cycles);
  ++cases;
}
void expect(LifetimeGuard& g,unsigned count,bool protected_write=false) {
  CHECK(copies==count);CHECK(unknowns==0);
#ifdef SH3_ENABLE_OBSERVER
  CHECK(events.size()==(check_callbacks?count:0));
  if(protected_write&&observing){CHECK(g.report().reason==LifetimeReason::protected_write);return;}
#else
  CHECK(events.empty());
  (void)protected_write;
#endif
  CHECK(g.report().state==LifetimeState::armed);
}
void spr_tests() {
  for(unsigned n:{1u,2u,4u,8u,16u,31u,32u,64u})run([=](auto& g){memcpy_from_spr(ram.data()+0x3000,32,n);CHECK(std::memcmp(ram.data()+0x3000,reinterpret_cast<u8*>(scratch.data())+32,n)==0);CHECK(ram[0x3000+n]==0xa5);expect(g,1,true);});
  run([](auto& g){memcpy_from_spr(ram.data()+0x2ff0,16368,32);CHECK(std::memcmp(ram.data()+0x2ff0,&scratch[1023],16)==0);CHECK(std::memcmp(ram.data()+0x3000,&scratch[0],16)==0);expect(g,2,true);});
  run([](auto& g){memcpy_from_spr(ram.data()+0x5000,16368,16);CHECK(zero_copies==1);expect(g,1);});
  run([](auto& g){memcpy_from_spr(ram.data()+0x3000,0,0);expect(g,0);});
  run([](auto& g){memcpy_from_spr(other.data(),0,32);expect(g,1);CHECK(g.report().accepted==0);});
  run([](auto& g){scratch[0].bytes.fill(0xa5);memcpy_from_spr(ram.data()+0x3000,0,16);CHECK(ram[0x3000]==0xa5);expect(g,1,true);});
  run([](auto& g){memcpy_from_spr(ram.data()+0x3000,0,16);scratch[0].bytes.fill(0xa5);memcpy_from_spr(ram.data()+0x3000,0,16);CHECK(ram[0x3000]==0xa5);expect(g,2,true);});
  run([](auto& g){memcpy_from_spr(ram.data()+0x3000,0,16);expect(g,1,true);},false);
}
void mfifo_tests() {
  for(unsigned n:{0u,1u,4u,5u,8u,9u})run([=](auto& g){
    dmacRegs.rbor.ADDR=0x5000;dmacRegs.rbsr.RMSK=48;
    CHECK(hwMFIFOWrite(0x5000,payload.data(),n));
    // Independent byte oracle for the pinned helper's actual two-copy behavior.
    std::array<u8,64> expected;expected.fill(0xa5);
    if(n<4)std::memcpy(expected.data(),payload.data(),n*16);
    else {std::memcpy(expected.data(),payload.data(),64);std::memcpy(expected.data(),payload.data()+4,(n%4)*16);}
    CHECK(std::memcmp(ram.data()+0x5000,expected.data(),64)==0);CHECK(ram[0x5040]==0xa5);
    expect(g,n==0?0:(n>4&&n%4?2:1));
  });
  run([](auto& g){dmacRegs.rbor.ADDR=0x3000;dmacRegs.rbsr.RMSK=48;CHECK(hwMFIFOWrite(0x3030,payload.data(),2));CHECK(std::memcmp(ram.data()+0x3030,&payload[0],16)==0);CHECK(std::memcmp(ram.data()+0x3000,&payload[1],16)==0);expect(g,2,true);});
  run([](auto& g){dmacRegs.rbor.ADDR=0x5000;dmacRegs.rbsr.RMSK=48;CHECK(hwMFIFOWrite(0x5030,payload.data(),1));CHECK(zero_copies==1);expect(g,1);});
  run([](auto& g){mapped=false;CHECK(!hwMFIFOWrite(0,payload.data(),1));CHECK(bus_errors==1);expect(g,0);});
  run([](auto& g){check_callbacks=false;uint pos=3;MemCopy_WrappedDest(payload.data(),reinterpret_cast<u128*>(other.data()),pos,4,2);CHECK(pos==1);expect(g,2);});
  run([](auto& g){dmacRegs.rbor.ADDR=0x3000;dmacRegs.rbsr.RMSK=48;payload[0].bytes.fill(0xa5);CHECK(hwMFIFOWrite(0x3000,payload.data(),1));expect(g,1,true);payload[0].bytes.fill(9);CHECK(hwMFIFOWrite(0x3000,payload.data(),1));payload[0].bytes.fill(0xa5);CHECK(hwMFIFOWrite(0x3000,payload.data(),1));CHECK(ram[0x3000]==0xa5);expect(g,3,true);});
}
void sif_tests() {
  for(bool second:{false,true})for(int kind=0;kind<7;++kind)run([=](auto& g){
    auto& sif=second?sif2:sif0;auto& ch=second?sif2dma:sif0ch;
    for(unsigned i=0;i<128;++i)sif.fifo.data[i]=0x11110000+i;
    sif.fifo.readPos=kind==1?124:0;sif.fifo.size=8;ch.qwc=2;
    if(kind==2)ch.qwc=0;
    if(kind==3)resolved=nullptr;
    if(kind==4)resolved=other.data();
    if(kind==5){resolved=ram.data()+0x3000;std::fill_n(sif.fifo.data,128,0xa5a5a5a5);}
    if(kind==6){sif.fifo.size=4;ch.qwc=3;}
    const auto before=ch.madr;const auto original_pos=sif.fifo.readPos;
    CHECK((second?s2::WriteFifoToEE():s0::WriteFifoToEE())==(kind!=3));
    unsigned moved=kind==2||kind==3?0:(kind==6?16:32);
    CHECK(ch.madr==before+moved);CHECK(sif.ee.cycles==static_cast<int>(moved/16));
    if(moved){auto* out=reinterpret_cast<u32*>(resolved);for(unsigned i=0;i<moved/4;++i)CHECK(out[i]==sif.fifo.data[(original_pos+i)%128]);}
    expect(g,moved?(kind==1?2:1):0,kind==5);
    if(kind==4)CHECK(g.report().accepted==0);
    if(kind==6){resolved=nullptr;CHECK(!(second?s2::WriteFifoToEE():s0::WriteFifoToEE()));CHECK(ch.madr==before+16);expect(g,1);}
  });
  for(bool second:{false,true})run([=](auto& g){auto& sif=second?sif2:sif0;auto& ch=second?sif2dma:sif0ch;resolved=ram.data()+0x3000;std::fill_n(sif.fifo.data,128,9);sif.fifo.size=4;ch.qwc=1;CHECK(second?s2::WriteFifoToEE():s0::WriteFifoToEE());expect(g,1,true);std::fill_n(sif.fifo.data,128,0xa5a5a5a5);sif.fifo.size=4;ch.qwc=1;CHECK(second?s2::WriteFifoToEE():s0::WriteFifoToEE());CHECK(ram[0x3000]==0xa5);expect(g,2,true);});
}
void ipu_tests() {
  for(unsigned kind=0;kind<6;++kind)run([=](auto& g){
    IPU_Fifo_Output fifo;for(unsigned i=0;i<32;++i)fifo.data[i]=0x22220000+i;
    fifo.readpos=kind==1||kind==2?28:0;auto initial=fifo.readpos;
    auto size=kind==2?1u:(kind==3?0u:2u);ipuRegs.ctrl.OFC=2;
    auto* out=kind==4?other.data():ram.data()+0x3000;
    if(kind==5)std::fill_n(fifo.data,32,0xa5a5a5a5);
    fifo.read(out,size);CHECK(ipuRegs.ctrl.OFC==2-size);CHECK(fifo.readpos==((initial+static_cast<int>(size*4))&31));
    for(unsigned i=0;i<size*4;++i)CHECK(reinterpret_cast<u32*>(out)[i]==fifo.data[(initial+i)%32]);
    expect(g,size?(kind==1?2:1):0,size&&kind!=4);if(kind==4)CHECK(g.report().accepted==0);
  });
  run([](auto& g){IPU_Fifo_Output fifo;std::fill_n(fifo.data,32,9);ipuRegs.ctrl.OFC=2;fifo.read(ram.data()+0x3000,1);expect(g,1,true);std::fill_n(fifo.data,32,0xa5a5a5a5);fifo.read(ram.data()+0x3000,1);CHECK(ram[0x3000]==0xa5);expect(g,2,true);});
}
void gs_tests() {
  for(unsigned kind=0;kind<5;++kind)run([=](auto& g){
    vif1ch.qwc=2;vif1.GSLastDownloadSize=kind==4?1:2;
    if(kind==1)resolved=nullptr;if(kind==2)vif1ch.qwc=0;
    defer_gs=kind==3;vif1TransferToMemory();
    if(kind==1){CHECK(gs_calls==0&&interrupts==1&&dmacRegs.stat.BEIS&&vif1.done);CHECK(g.report().state==LifetimeState::armed);return;}
    CHECK(gs_calls==1);auto size=kind==2?0u:(kind==4?1u:2u);
#ifdef SH3_ENABLE_OBSERVER
    CHECK(unknowns==(size?1u:0u));CHECK(g.report().state==(size?LifetimeState::failed:LifetimeState::armed));
    if(size)CHECK(g.report().reason==LifetimeReason::lost);
#else
    CHECK(unknowns==0);CHECK(g.report().state==LifetimeState::armed);
#endif
    CHECK(g_vif1Cycles==size*2);CHECK(vif1ch.madr==0x5000+size*16);
    if(defer_gs){CHECK(ram[0x5000]==0xa5);CHECK(queued_dst==resolved&&queued_size==size);std::memset(queued_dst,0x5a,queued_size*16);}
    if(size)CHECK(ram[0x5000]==0x5a&&ram[0x5000+size*16]==0xa5);
  });
}
int main(){
  CHECK(cpuRegs.cycle==1001);spr_tests();mfifo_tests();sif_tests();ipu_tests();gs_tests();
  CHECK(cases==54);
  std::printf("{\"cases\":%u,\"effects_digest\":\"%016llx\",\"result\":\"PASS\"}\n",cases,static_cast<unsigned long long>(digest));
}
