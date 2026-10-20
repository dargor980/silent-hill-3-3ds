// Own data and doubles; exact provider fragments are supplied by the private stage.
#include "check.hpp"
#include "sh3_observer/capture.hpp"
#include "sh3_observer/physical_writes.hpp"
#include <algorithm>
#include <array>
#include <cstdint>
#include <cstdio>
#include <cstring>
#include <string>
#include <utility>
#include <vector>
using namespace sh3::observer;
using u8=std::uint8_t;using u16=std::uint16_t;using u32=std::uint32_t;using u64=std::uint64_t;using uptr=std::uintptr_t;using uint=unsigned;
struct u128 {u64 lo{},hi{};};
struct Register {union {u64 UD[2]{};std::int64_t SD[2];u32 UL[4];};};
struct {struct{struct{Register a0,a1;}n;}GPR;u64 cycle=1001;}cpuRegs;
namespace Ps2MemSize {constexpr u32 ExposedRam=ram_size,MainRam=ram_size,ExtraRam=0x1000;}
struct alignas(4096) Memory {alignas(4096)u8 Main[ram_size]{};alignas(4096)u8 Scratch[16384]{};}memory;
Memory* eeMem=&memory;
alignas(4096) std::array<u8,4096> other;
void* PSM(u32 address){u32 a=address&0x1fffffff;CHECK(a<ram_size);return eeMem->Main+a;}
template<class... T>void logargs(T...){}
struct Logger{template<class... T>void WriteLn(T...){}template<class... T>void Warning(T...){}template<class... T>void Error(T...){}}Console,DevCon;
#define BIOS_LOG(...) logargs(__VA_ARGS__)
#define DEBUG_LAUNCHARG 0
constexpr unsigned VTLB_PAGE_BITS=12,VTLB_PAGE_SIZE=4096,VTLB_PAGE_MASK=4095;
namespace vtlb_private {
struct VTLBVirtual{uptr bias{};bool special=true;bool isHandler(u32)const{return special;}uptr assumePtr(u32 a)const{return bias+a;}};
struct{std::array<VTLBVirtual,32> vmap;}vtlbdata;
}
using vtlb_private::vtlbdata;
LifetimeGuard* guard_ptr=nullptr;bool observing=true;
struct Event{u64 address,size;std::vector<u8> before;};
std::vector<Event> events;unsigned unknowns=0,cases=0;
namespace sh3::observer {void harness_write(u64,u64,u64)noexcept;void harness_unknown(u64)noexcept;}
#define before_host_write harness_write
#define before_untracked_write harness_unknown
#include "ram-write.inc"
#include "safe-write.inc"
#include "safe-read.inc"
#include "safe-compare.inc"
u32 memRead32(u32 a){u32 v{};CHECK(vtlb_memSafeReadBytes(a,&v,4));return v;}
// Dependency double for boot pointer-table writes; real VTLB RAM leaf below it.
void memWrite32(u32 a,u32 v){CHECK(vtlb_ramWrite(a,v));}
const int kMaxArgs=16;uptr g_argPtrs[kMaxArgs]{};u32 g_osdsys_str=0;
// Fixture addresses, not addresses observed in Silent Hill 3.
constexpr u32 EELOAD_START=0x3000,EELOAD_SIZE=0x100;
bool AllowParams1=false,AllowParams2=false,extra_memory=false;
#define CHECK_EXTRAMEM extra_memory
struct{std::string CurrentGameArgs;}EmuConfig;
std::vector<std::array<u32,3>> maps;std::vector<std::array<u32,2>> unmaps;
bool expect_unmap_notice=false;
void vtlb_VMap(u32 a,u32 b,u32 size){maps.push_back({a,b,size});}
void vtlb_VMapUnmap(u32 a,u32 size){
#ifdef SH3_ENABLE_OBSERVER
 if(observing&&expect_unmap_notice)CHECK(guard_ptr->report().reason==LifetimeReason::lost);
#endif
 unmaps.push_back({a,size});
}
namespace VMManager::Internal {
bool fast=false;std::string override_name,loaded;unsigned disabled=0;
bool IsFastBootInProgress(){return fast;}const std::string& GetELFOverride(){return override_name;}
void DisableFastBoot(){++disabled;fast=false;}void ELFLoadingOnCPUThread(std::string name){loaded=std::move(name);}
}
namespace Path {std::string GetFileName(const std::string& p){return p.substr(p.find_last_of('/')+1);}}
namespace fmt {std::string format(const char*,const std::string& s){return "host:"+s;}}
enum class CDVDDiscType{PS2Disc,Other};CDVDDiscType disc_type=CDVDDiscType::Other;std::string disc_elf;
void cdvdGetDiscInfo(void*,std::string* elf,void*,void*,CDVDDiscType* type){*elf=disc_elf;*type=disc_type;}
#include "parse-args.inc"
#include "load-first.inc"
#include "load-second.inc"
u32 deci2addr=0,deci2handler=0;char deci2buffer[256]{};bool dma_missing=false;
void* dmaGetAddr(u32 a,bool){return dma_missing?nullptr:PSM(a&~15u);}
std::string ShiftJIS_ConvertString(const char* p){return p;}
std::string console_text;void eeConLog(const std::string& s){console_text=s;}void eeDeci2Log(const std::string& s){console_text=s;}
#include "deci.inc"
namespace Achievements::RAIntegration {void RACallbackWriteMemory(unsigned int,unsigned char);}
u32 GetExposedEEMemorySize(){return ram_size+sizeof(memory.Scratch);}
#include "ra-write.inc"
// Open-source provider layout/address: only own synthetic table data are loaded.
#include "tlb-layout.inc"
constexpr u32 table_offset=0x3d5580;
#include "tlb-unload.inc"
class MemoryInterface {
public:
 virtual ~MemoryInterface()=default;
 virtual u32 Read32(u32,bool*)=0;virtual bool Write32(u32,u32)=0;
 virtual bool WriteBytes(u32,const void*,u32)=0;virtual bool CompareBytes(u32,const void*,u32)=0;
 bool IdempotentWrite32(u32,u32);bool IdempotentWriteBytes(u32,void*,u32);
};
class R5900DebugInterface:public MemoryInterface {
public:
 bool allowed=true;bool isValidAddress(u32){return allowed;}
 u32 Read32(u32 a,bool* ok)override{u32 v{};*ok=vtlb_memSafeReadBytes(a,&v,4);return v;}
 bool Write8(u32,u8);bool Write16(u32,u16);bool Write32(u32,u32)override;
 bool Write64(u32,u64);bool Write128(u32,u128);bool WriteBytes(u32,const void*,u32)override;
 bool CompareBytes(u32 a,const void* p,u32 n)override{return vtlb_memSafeCmpBytes(a,p,n)==0;}
};
#include "debug-writes.inc"
#include "idempotent-scalar.inc"
#include "idempotent-bytes.inc"
#undef before_host_write
#undef before_untracked_write
namespace sh3::observer {
void harness_write(u64 address,u64 size,u64 cycle)noexcept{
 CHECK(cycle==1001&&size>0&&size<8192);
 const auto* p=reinterpret_cast<const u8*>(address);
 events.push_back({address,size,{p,p+size}});before_host_write(address,size,cycle);
}
void harness_unknown(u64 cycle)noexcept{CHECK(cycle==1001);++unknowns;before_untracked_write(cycle);}
}
u64 digest=14695981039346656037ULL;
void hash(u64 value){for(unsigned i=0;i<8;++i){digest^=(value>>(i*8))&255;digest*=1099511628211ULL;}}
void string_at(u32 a,const std::string& s){std::memcpy(PSM(a),s.c_str(),s.size()+1);}
void word_at(u32 a,u32 v){std::memcpy(PSM(a),&v,4);}
LifetimePlan plan(){return {{{{1}},7,100,1000},{0x1000,0x2000,0x3000,0x4000},1000};}
template<class F>void run(F test,bool bind=true){
 std::fill_n(memory.Main,0x10000,0xa5);std::memset(memory.Main+table_offset,0,150*sizeof(GoemonTlb));std::memset(memory.Scratch,0xa5,sizeof(memory.Scratch));other.fill(0xa5);
 cpuRegs={};cpuRegs.cycle=1001;events.clear();unknowns=0;observing=bind;std::fill_n(g_argPtrs,kMaxArgs,0);g_osdsys_str=0;
 AllowParams1=AllowParams2=extra_memory=expect_unmap_notice=false;EmuConfig.CurrentGameArgs.clear();maps.clear();unmaps.clear();
 VMManager::Internal::fast=false;VMManager::Internal::override_name.clear();VMManager::Internal::loaded.clear();VMManager::Internal::disabled=0;
 disc_type=CDVDDiscType::Other;disc_elf.clear();deci2addr=deci2handler=0;std::memset(deci2buffer,0,sizeof(deci2buffer));dma_missing=false;console_text.clear();
 auto base=reinterpret_cast<uptr>(memory.Main);for(auto& m:vtlbdata.vmap)m={0,true};
 for(unsigned i=0;i<8;++i)vtlbdata.vmap[i]={base,false};
 vtlbdata.vmap[9]={base-0x6000,false};vtlbdata.vmap[10]={reinterpret_cast<uptr>(other.data())-0xa000,false};
 LifetimeGuard guard;CHECK(guard.arm(plan()));guard_ptr=&guard;PhysicalWrites bridge(guard,base);
 if(bind){WriteBinding connection(bridge);CHECK(connection.connected());test(guard);}else test(guard);
 for(unsigned i=0;i<0x10000;++i)hash(memory.Main[i]);for(auto v:memory.Scratch)hash(v);for(auto v:other)hash(v);
 for(unsigned i=0;i<150*sizeof(GoemonTlb);++i)hash(memory.Main[table_offset+i]);
 for(auto v:g_argPtrs)hash(v);hash(cpuRegs.GPR.n.a0.UD[0]);hash(cpuRegs.GPR.n.a1.UD[0]);hash(g_osdsys_str);hash(deci2addr);hash(deci2handler);
 for(auto v:VMManager::Internal::loaded)hash(v);hash(VMManager::Internal::disabled);hash(AllowParams1);hash(AllowParams2);
 for(const auto& m:maps)for(auto v:m)hash(v);for(const auto& m:unmaps)for(auto v:m)hash(v);for(auto v:console_text)hash(v);
 ++cases;
}
void expect(LifetimeGuard& g,unsigned writes,LifetimeReason reason=LifetimeReason::none,unsigned lost=0){
#ifdef SH3_ENABLE_OBSERVER
 CHECK(events.size()==writes&&unknowns==lost);
 if(observing&&reason!=LifetimeReason::none){CHECK(g.report().state==LifetimeState::failed&&g.report().reason==reason);return;}
#else
 (void)writes;(void)reason;(void)lost;CHECK(events.empty()&&unknowns==0);
#endif
 CHECK(g.report().state==LifetimeState::armed);
}
void prior(unsigned index,u32 offset,const std::vector<u8>& bytes){
#ifdef SH3_ENABLE_OBSERVER
 CHECK(index<events.size());CHECK(events[index].address==reinterpret_cast<uptr>(memory.Main+offset));CHECK(events[index].before==bytes);
#else
 (void)index;(void)offset;(void)bytes;
#endif
}
void argument_tests(){
 run([](auto& g){CHECK(ParseArgumentString(0)==0);expect(g,0);});
 run([](auto& g){string_at(0x3000,"");CHECK(ParseArgumentString(0x3000)==0);expect(g,0);});
 run([](auto& g){string_at(0x3000,"alpha");CHECK(ParseArgumentString(0x3000)==1&&g_argPtrs[0]==0x3000);expect(g,0);});
 run([](auto& g){string_at(0x3000,"a  b");CHECK(ParseArgumentString(0x3000)==2&&g_argPtrs[1]==0x3003);CHECK(memory.Main[0x3001]==0&&memory.Main[0x3002]==0);prior(0,0x3001,{' '});prior(1,0x3002,{' '});expect(g,2,LifetimeReason::protected_write);});
 run([](auto& g){string_at(0x5000," a b ");CHECK(ParseArgumentString(0x5000)==2);expect(g,3);});
 run([](auto& g){std::string s;for(unsigned i=0;i<18;++i)s+="a ";string_at(0x5000,s);CHECK(ParseArgumentString(0x5000)==16);CHECK(memory.Main[0x5021]==' ');expect(g,16);});
 run([](auto& g){string_at(0x3000,"a b");CHECK(ParseArgumentString(0x3000)==2);expect(g,1);},false);
}
void second_boot_tests(){
 run([](auto& g){eeloadHook2();expect(g,0);});
 run([](auto& g){EmuConfig.CurrentGameArgs="x";eeloadHook2();expect(g,0);});
 for(bool bind:{true,false})run([](auto& g){g_osdsys_str=0x3000;string_at(0x3000,"fixture");EmuConfig.CurrentGameArgs="one two";eeloadHook2();CHECK(cpuRegs.GPR.n.a0.SD[0]==3&&cpuRegs.GPR.n.a1.UD[0]==0x2ff4);CHECK(memRead32(0x2ff4)==0x3000&&memRead32(0x2ffc)==0x300c);CHECK(std::strcmp(static_cast<char*>(PSM(0x3008)),"one")==0);prior(0,0x3007,{0});prior(1,0x3008,std::vector<u8>(8,0xa5));expect(g,7,LifetimeReason::protected_write);},bind);
 run([](auto& g){g_osdsys_str=0x5000;string_at(0x5000,"f");EmuConfig.CurrentGameArgs=" ";eeloadHook2();CHECK(cpuRegs.GPR.n.a0.SD[0]==1);expect(g,5);});
}
void first_boot_tests(){
 run([](auto& g){eeloadHook();CHECK(VMManager::Internal::loaded.empty());expect(g,0);});
 run([](auto& g){cpuRegs.GPR.n.a0.SD[0]=2;cpuRegs.GPR.n.a1.UD[0]=0x6000;word_at(0x6004,0x5000);string_at(0x5000,"fixture");EmuConfig.CurrentGameArgs="ignored";eeloadHook();CHECK(VMManager::Internal::loaded=="fixture");expect(g,0);});
 run([](auto& g){cpuRegs.GPR.n.a0.SD[0]=2;cpuRegs.GPR.n.a1.UD[0]=0x6000;word_at(0x6000,0x3000);word_at(0x6004,0x3007);string_at(0x3000,"EELOAD");string_at(0x3007,"rom0:PS2LOGO");EmuConfig.CurrentGameArgs="x";eeloadHook();CHECK(cpuRegs.GPR.n.a0.SD[0]==3&&memRead32(0x6008)==0x3014);CHECK(VMManager::Internal::loaded=="rom0:PS2LOGO");prior(0,0x3006,{0});prior(1,0x3013,{0});expect(g,8,LifetimeReason::protected_write);});
 for(bool bind:{true,false})run([](auto& g){VMManager::Internal::fast=true;VMManager::Internal::override_name="/fixture/demo.elf";string_at(EELOAD_START,"rom0:OSDSYS");eeloadHook();CHECK(VMManager::Internal::loaded=="host:demo.elf");CHECK(std::strcmp(static_cast<char*>(PSM(EELOAD_START)),"host:demo.elf")==0);expect(g,1,LifetimeReason::protected_write);},bind);
 run([](auto& g){VMManager::Internal::fast=true;disc_type=CDVDDiscType::PS2Disc;disc_elf="fixture.elf";string_at(EELOAD_START,"rom0:OSDSYS");eeloadHook();CHECK(VMManager::Internal::loaded==disc_elf);expect(g,1,LifetimeReason::protected_write);});
 run([](auto& g){VMManager::Internal::fast=true;disc_elf="other.elf";eeloadHook();CHECK(VMManager::Internal::disabled==1&&AllowParams1&&AllowParams2);expect(g,0);});
 run([](auto& g){extra_memory=true;eeloadHook();CHECK(maps.size()==3);expect(g,0);});
}
void deci_tests(){
 run([](auto& g){CHECK(__Deci2Call(17,nullptr)==-1&&__Deci2Call(0,nullptr)==0);expect(g,0);});
 run([](auto& g){u32 a[4]={0,0x3000,0x5678,0};CHECK(__Deci2Call(1,a)==1&&deci2addr==0x3000&&deci2handler==0x5678);expect(g,0);});
 run([](auto& g){CHECK(__Deci2Call(1,nullptr)==1&&deci2handler==0);expect(g,0);});
 run([](auto& g){deci2addr=3;deci2handler=4;CHECK(__Deci2Call(2,nullptr)==1&&deci2addr==0&&deci2handler==0);expect(g,0);});
 run([](auto& g){CHECK(__Deci2Call(3,nullptr)==1);expect(g,0);});
 for(unsigned kind=0;kind<4;++kind)run([=](auto& g){deci2addr=0x3000;word_at(0x3004,12);word_at(0x300c,kind==1?0:0x87654321);CHECK(__Deci2Call(3,nullptr)==1&&memRead32(0x300c)==0);if(kind==2){word_at(0x300c,0x87654321);CHECK(__Deci2Call(3,nullptr)==1);}expect(g,kind==2?2:1,LifetimeReason::protected_write);},kind!=3);
 for(bool fallback:{false,true})run([=](auto& g){dma_missing=fallback;deci2addr=0x3000;word_at(0x3004,15);word_at(0x3010,0x5011);string_at(0x501d,"abc");CHECK(__Deci2Call(3,nullptr)==1&&console_text=="abc");expect(g,1,LifetimeReason::protected_write);});
 for(int call:{4,5,6,16})run([=](auto& g){CHECK(__Deci2Call(call,nullptr)==1);expect(g,0);});
}
void ra_tests(){
 using Achievements::RAIntegration::RACallbackWriteMemory;
 run([](auto& g){RACallbackWriteMemory(0x3000,0x39);CHECK(memory.Main[0x3000]==0x39);prior(0,0x3000,{0xa5});expect(g,1,LifetimeReason::protected_write);});
 run([](auto& g){RACallbackWriteMemory(0x3000,0xa5);expect(g,1,LifetimeReason::protected_write);});
 run([](auto& g){RACallbackWriteMemory(0x3000,0x39);RACallbackWriteMemory(0x3000,0xa5);CHECK(memory.Main[0x3000]==0xa5);expect(g,2,LifetimeReason::protected_write);});
 run([](auto& g){RACallbackWriteMemory(ram_size,0x39);CHECK(memory.Scratch[0]==0x39);expect(g,1);CHECK(g.report().accepted==0);});
 run([](auto& g){RACallbackWriteMemory(GetExposedEEMemorySize(),0x39);RACallbackWriteMemory(0xffffffff,0x39);expect(g,0);});
 run([](auto& g){RACallbackWriteMemory(0x5000,0x39);expect(g,1);});
 run([](auto& g){RACallbackWriteMemory(0x3000,0x39);expect(g,1);},false);
}
void unload_tests(){
 run([](auto& g){GoemonUnloadTlb(42);CHECK(unmaps.empty());expect(g,0);});
 run([](auto& g){auto* t=reinterpret_cast<GoemonTlb*>(memory.Main+table_offset);t[0].key=42;t[0].low_add=0x5000;t[0].high_add=0x6000;GoemonUnloadTlb(42);CHECK(t[0].key==42&&unmaps.empty());expect(g,0);});
 for(bool bind:{true,false})run([](auto& g){auto* t=reinterpret_cast<GoemonTlb*>(memory.Main+table_offset);t[0].valid=1;t[0].key=42;t[0].low_add=0x5000;t[0].high_add=0x6000;t[0].physical_add=0x7000;t[1]=t[0];expect_unmap_notice=true;GoemonUnloadTlb(42);CHECK(unmaps.size()==4&&t[0].valid==0&&t[0].key==0xfefefefe&&t[1].physical_add==0x7000);expect(g,0,LifetimeReason::lost,2);},bind);
}
template<class T>bool debug_write(R5900DebugInterface& d,u32 a,T v){
 if constexpr(sizeof(T)==1)return d.Write8(a,v);else if constexpr(sizeof(T)==2)return d.Write16(a,v);else if constexpr(sizeof(T)==4)return d.Write32(a,v);else if constexpr(sizeof(T)==8)return d.Write64(a,v);else return d.Write128(a,v);
}
template<class T>void width_tests(){
 for(unsigned mode=0;mode<3;++mode)run([=](auto& g){R5900DebugInterface d;d.allowed=mode!=1;T v{};std::memset(&v,0x39,sizeof(v));u32 a=mode==2?0xa000:0x9000;CHECK(debug_write(d,a,v)==d.allowed);if(d.allowed)CHECK(std::memcmp(mode==2?other.data():memory.Main+0x3000,&v,sizeof(v))==0);expect(g,mode==1?0:1,mode==0?LifetimeReason::protected_write:LifetimeReason::none);});
 for(unsigned mode=0;mode<3;++mode)run([=](auto& g){T v{};std::memset(&v,0x39,sizeof(v));u32 a=mode==0?0x9000:mode==1?0x8000:0xa000;CHECK(vtlb_ramWrite(a,v)==(mode!=1));expect(g,mode==1?0:1,mode==0?LifetimeReason::protected_write:LifetimeReason::none);});
}
void delegated_tests(){
 width_tests<u8>();width_tests<u16>();width_tests<u32>();width_tests<u64>();width_tests<u128>();
 run([](auto& g){R5900DebugInterface d;std::array<u8,8> b;b.fill(0x39);CHECK(d.WriteBytes(0x2ffc,b.data(),8));prior(0,0x2ffc,std::vector<u8>(4,0xa5));prior(1,0x3000,std::vector<u8>(4,0xa5));CHECK(memory.Main[0x3003]==0x39);expect(g,2,LifetimeReason::protected_write);});
 run([](auto& g){R5900DebugInterface d;std::array<u8,8> b;b.fill(0x39);CHECK(!d.WriteBytes(0x7ffc,b.data(),8));CHECK(memory.Main[0x7ffc]==0x39&&memory.Main[0x8000]==0xa5);expect(g,1);});
 run([](auto& g){R5900DebugInterface d;u8 v=9;CHECK(!d.WriteBytes(0x8000,&v,1));CHECK(d.WriteBytes(0x8000,&v,0));expect(g,0);});
 run([](auto& g){R5900DebugInterface d;CHECK(d.IdempotentWrite32(0x3000,0xa5a5a5a5));expect(g,0);});
 run([](auto& g){R5900DebugInterface d;CHECK(d.IdempotentWrite32(0x3000,0x39));CHECK(d.IdempotentWrite32(0x3000,0xa5a5a5a5));CHECK(memRead32(0x3000)==0xa5a5a5a5);expect(g,2,LifetimeReason::protected_write);});
 run([](auto& g){R5900DebugInterface d;CHECK(!d.IdempotentWrite32(0x8000,0));expect(g,0);});
 run([](auto& g){R5900DebugInterface d;std::array<u8,4> b;b.fill(0xa5);CHECK(d.IdempotentWriteBytes(0x3000,b.data(),4));expect(g,0);});
 run([](auto& g){R5900DebugInterface d;std::array<u8,4> b;b.fill(0x39);CHECK(d.IdempotentWriteBytes(0x3000,b.data(),4));expect(g,1,LifetimeReason::protected_write);});
 run([](auto& g){R5900DebugInterface d;std::array<u8,8> b;b.fill(0x39);CHECK(!d.IdempotentWriteBytes(0x7ffc,b.data(),8));expect(g,1);});
}
int main(){argument_tests();second_boot_tests();first_boot_tests();deci_tests();ra_tests();unload_tests();delegated_tests();
 std::printf("{\"cases\":%u,\"effects_digest\":\"%016llx\",\"result\":\"PASS\"}\n",cases,static_cast<unsigned long long>(digest));
}
