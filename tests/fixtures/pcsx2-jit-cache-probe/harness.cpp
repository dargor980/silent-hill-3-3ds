// Own fixtures. Generated provider bodies live in the private stage.
// Map, CPU registers, logger, fastjmp and compiled-entry callbacks are doubles.
#include "check.hpp"
#include "sh3_observer/capture.hpp"
#include "sh3_observer/physical_writes.hpp"
#include <algorithm>
#include <array>
#include <cstdint>
#include <cstdio>
#include <cstring>
#include <type_traits>
#include <vector>
using namespace sh3::observer;
using u8=std::uint8_t;using u16=std::uint16_t;using u32=std::uint32_t;using u64=std::uint64_t;using uptr=std::uintptr_t;using uint=unsigned;
struct alignas(16) u128 {u64 lo{},hi{};};using mem128_t=u128;using r128=u128;
#define RETURNS_R128 r128
#define TAKES_R128
template<class... T> void logargs(T...) {}
#define CACHE_LOG(...) logargs(__VA_ARGS__)
#define pxAssertMsg(x,...) CHECK(x)
struct Logger {template<class... T>void Error(T...){} template<class... T>void Warning(T...){} } Console,DevCon;
namespace R5900 {}
struct {struct{struct{u32 Config=0x10000,TagLo=0;}n;}CP0;struct{struct{u32 UL[4]{};}r[32];}GPR;u64 cycle=1001;u32 code=0;}cpuRegs;
unsigned rs=0,op=0;int imm=0;
#define _Rs_ rs
#define _Rt_ op
#define _Imm_ imm
bool ee_rec=false,cache_enabled=true;
#define CHECK_EEREC ee_rec
#define CHECK_CACHE cache_enabled
bool CheckCache(u32){return true;}
constexpr unsigned VTLB_PAGE_BITS=12;
alignas(4096) std::array<u8,ram_size> ram;
alignas(4096) std::array<u8,4096> other;
std::array<u8,16> handler_bytes;
u128 r128_to_u128(r128 v){return v;}
r128 r128_load(const void* p){r128 r;std::memcpy(&r,p,16);return r;}
void r128_store_unaligned(void* p,r128 v){std::memcpy(p,&v,16);}
template<int Bits> struct Value;
template<> struct Value<8>{using type=u8;};template<>struct Value<16>{using type=u16;};
template<>struct Value<32>{using type=u32;};template<>struct Value<64>{using type=u64;};template<>struct Value<128>{using type=u128;};
LifetimeGuard* guard_ptr=nullptr;bool observing=true;
unsigned unknowns=0,cases=0;
struct Event{u64 address,size;std::array<u8,64> before;};std::vector<Event> events;
template<int Bits>void handler(u32,typename Value<Bits>::type value){
#ifdef SH3_ENABLE_OBSERVER
 if(observing)CHECK(guard_ptr->report().reason==LifetimeReason::lost);
#endif
 std::memcpy(handler_bytes.data(),&value,sizeof(value));
}
namespace vtlb_private {
struct VTLBVirtual {
 uptr bias{};bool special{};
 bool isHandler(u32)const{return special;} uptr assumePtr(u32 a)const{return bias+a;}
 u32 assumeHandlerGetPAddr(u32 a)const{return a;}
 template<int Bits,bool Write>auto assumeHandler()const{static_assert(Write);return &handler<Bits>;}
};
struct{std::array<VTLBVirtual,32> vmap;}vtlbdata;
}
namespace sh3::observer {
void harness_write(u64,u64,u64)noexcept;
void harness_unknown(u64)noexcept;
}
#define before_host_write harness_write
#define before_untracked_write harness_unknown
#include "cache.inc"
// Default arguments are supplied by Cache.h in the real provider.
void writeCache8(u32,u8,bool=true);void writeCache16(u32,u16,bool=true);
void writeCache32(u32,u32,bool=true);void writeCache64(u32,u64,bool=true);
void writeCache128(u32,const mem128_t*,bool=true);
#include "vtlb-scalar.inc"
#include "vtlb-128.inc"
bool eeRecNeedsReset=false,eeCpuExecuting=false;
int m_SetJmp_StateCheck=0,jump_result=0;
unsigned resets=0,entries=0,prints=0;
bool expect_jit_barrier=false;
std::vector<unsigned> order;
int fastjmp_set(int*){order.push_back(2);return jump_result;}
void recResetRaw(){order.push_back(1);++resets;
#ifdef SH3_ENABLE_OBSERVER
 if(observing&&expect_jit_barrier)CHECK(guard_ptr->report().reason==LifetimeReason::lost);
#endif
}
void preexisting_compiled_callback(){order.push_back(3);++entries;CHECK(eeCpuExecuting);
#ifdef SH3_ENABLE_OBSERVER
 if(observing&&expect_jit_barrier)CHECK(guard_ptr->report().reason==LifetimeReason::lost);
#endif
 ram[0x3000]=9;ram[0x3000]=0xa5;
}
void (*EnterRecompiledCode)()=&preexisting_compiled_callback;
namespace EE {struct{void Print(){order.push_back(4);++prints;}}Profiler;}
#include "jit-entry.inc"
#undef before_host_write
#undef before_untracked_write
u64 digest=14695981039346656037ULL;
u64 addhash(u64 h,u64 v){for(unsigned i=0;i<8;++i){h^=(v>>(i*8))&255;h*=1099511628211ULL;}return h;}
u64 cache_signature(){u64 h=0;for(const auto& s:cache.sets)for(unsigned w=0;w<2;++w){h=addhash(h,s.tags[w].rawValue);for(auto v:s.data[w].bytes)h=addhash(h,v);}return h;}
bool check_cache_before=false;u64 cache_before=0;
void before_cache(){check_cache_before=true;cache_before=cache_signature();}
namespace sh3::observer {
void harness_unknown(u64 cycle)noexcept{
 CHECK(cycle==1001);
 if(check_cache_before){CHECK(cache_signature()==cache_before);check_cache_before=false;}
 ++unknowns;before_untracked_write(cycle);
}
void harness_write(u64 address,u64 size,u64 cycle)noexcept{
 CHECK(cycle==1001);CHECK(size>0&&size<=64);
 Event e{address,size,{}};std::memcpy(e.before.data(),reinterpret_cast<void*>(address),size);events.push_back(e);
 before_host_write(address,size,cycle);
}
}
LifetimePlan plan(){return {{{{1}},7,100,1000},{0x1000,0x2000,0x3000,0x4000},1000};}
template<class F>void run(F test,bool bind=true){
 std::fill_n(ram.begin(),0x10000,0xa5);other.fill(0xa5);handler_bytes.fill(0);cache={};cpuRegs={};cpuRegs.cycle=1001;cpuRegs.CP0.n.Config=0x10000;
 op=rs=0;imm=0;ee_rec=false;cache_enabled=true;unknowns=0;events.clear();check_cache_before=false;observing=bind;
 eeRecNeedsReset=eeCpuExecuting=false;jump_result=0;resets=entries=prints=0;expect_jit_barrier=false;order.clear();
 const auto base=reinterpret_cast<uptr>(ram.data());
 for(auto& m:vtlbdata.vmap)m={0,true};
 for(unsigned page=1;page<5;++page)vtlbdata.vmap[page]={base+(page==3?0:0x4000),false};
 vtlbdata.vmap[9]=vtlbdata.vmap[1];vtlbdata.vmap[9].bias-=0x8000;
 vtlbdata.vmap[5]={reinterpret_cast<uptr>(other.data())-0x5000,false};
 LifetimeGuard guard;CHECK(guard.arm(plan()));guard_ptr=&guard;PhysicalWrites bridge(guard,base);
 if(bind){WriteBinding connection(bridge);CHECK(connection.connected());test(guard);}else test(guard);
 for(unsigned i=0;i<0x9000;++i)digest=addhash(digest,ram[i]);for(auto v:other)digest=addhash(digest,v);for(auto v:handler_bytes)digest=addhash(digest,v);
 // Normalize host addresses: compare cache state/data independently of ASLR.
 for(const auto& set:cache.sets)for(unsigned w=0;w<2;++w){digest=addhash(digest,set.tags[w].rawValue&0xfff);for(auto b:set.data[w].bytes)digest=addhash(digest,b);}
 digest=addhash(digest,cpuRegs.CP0.n.TagLo);digest=addhash(digest,resets);digest=addhash(digest,entries);digest=addhash(digest,prints);
 for(auto v:order)digest=addhash(digest,v);
 ++cases;
}
void expect(LifetimeGuard& g,unsigned lost,unsigned writes,LifetimeReason reason=LifetimeReason::none){
#ifdef SH3_ENABLE_OBSERVER
 CHECK(unknowns==lost);CHECK(events.size()==writes);
 CHECK(!check_cache_before);
 if(observing&&reason!=LifetimeReason::none){CHECK(g.report().state==LifetimeState::failed);CHECK(g.report().reason==reason);return;}
#else
 (void)lost;(void)writes;(void)reason;CHECK(events.empty()&&unknowns==0);
#endif
 CHECK(g.report().state==LifetimeState::armed);
}
template<class T>T value(){T v{};std::memset(&v,0x39,sizeof(v));return v;}
template<class T>void store(u32 a,T v,bool valid=true){writeCache<T>(a,v,valid);}
template<>void store(u32 a,u128 v,bool valid){writeCache128(a,&v,valid);}
template<class T>void vstore(u32 a,T v){vtlb_memWrite<T>(a,v);}
template<>void vstore(u32 a,u128 v){vtlb_memWrite128(a,v);}
template<class T>T load(u32 a){return readCache<T>(a,true);}
template<>u128 load(u32 a){return readCache128(a,true);}
template<class T>void width_tests(){
 run([](auto& g){auto v=value<T>();before_cache();store(0x1000,v);CHECK(ram[0x5000]==0xa5);auto got=load<T>(0x1000);CHECK(std::memcmp(&got,&v,sizeof(v))==0);writebackCache();CHECK(std::memcmp(ram.data()+0x5000,&v,sizeof(v))==0);CHECK(!cache.lineAt(0,0).tag.isDirty());expect(g,1,1,LifetimeReason::lost);});
 run([](auto& g){auto v=value<T>();before_cache();store(0x1000,v);store(0x1000,v);T altered{};store(0x1000,altered);store(0x1000,v);writebackCache();CHECK(std::memcmp(ram.data()+0x5000,&v,sizeof(v))==0);expect(g,4,1,LifetimeReason::lost);});
 run([](auto& g){auto v=value<T>();before_cache();vstore(0x1000,v);writebackCache();CHECK(std::memcmp(ram.data()+0x5000,&v,sizeof(v))==0);expect(g,1,1,LifetimeReason::lost);});
 run([](auto& g){cache_enabled=false;auto v=value<T>();vstore(0x3000,v);CHECK(std::memcmp(ram.data()+0x3000,&v,sizeof(v))==0);expect(g,0,1,LifetimeReason::protected_write);});
 run([](auto& g){auto v=value<T>();vstore(0x7000,v);CHECK(std::memcmp(handler_bytes.data(),&v,sizeof(v))==0);expect(g,1,0,LifetimeReason::lost);});
 run([](auto& g){auto v=value<T>();before_cache();store(0x7000,v,false);writebackCache();CHECK(ram[0x7000]==0xa5);expect(g,1,0,LifetimeReason::lost);});
}
CacheLine seed(unsigned offset,unsigned way=0,bool dirty=true,bool valid=true,bool pfn=true){
 auto line=cache.lineAt((offset>>6)&63,way);line.tag.rawValue=0;line.tag.setAddr(reinterpret_cast<uptr>(ram.data()+offset));
 if(dirty)line.tag.setDirty();if(valid)line.tag.setValid();line.tag.setValidPFN(pfn);std::memset(&line.data,0x39,64);return line;
}
void writeback_tests(){
 for(unsigned flags=0;flags<8;++flags)run([=](auto& g){auto line=seed(0x3000,0,flags&1,flags&2,flags&4);line.writeBackIfNeeded();bool wrote=flags==7;
#ifdef SH3_ENABLE_OBSERVER
  if(wrote)CHECK(events.size()==1&&events[0].before[0]==0xa5);
#endif
  CHECK(ram[0x3000]==(wrote?0x39:0xa5));if((flags&3)==3)CHECK(!line.tag.isDirty());expect(g,0,wrote?1:0,wrote?LifetimeReason::protected_write:LifetimeReason::none);});
 run([](auto& g){auto line=seed(0x3000);std::memset(&line.data,0xa5,64);line.writeBackIfNeeded();CHECK(ram[0x3000]==0xa5);expect(g,0,1,LifetimeReason::protected_write);});
 run([](auto& g){auto line=seed(0x3000);line.writeBackIfNeeded();std::memset(&line.data,0xa5,64);line.tag.setDirty();line.writeBackIfNeeded();CHECK(ram[0x3000]==0xa5);expect(g,0,2,LifetimeReason::protected_write);});
 run([](auto& g){auto line=seed(0x3000);line.tag.setAddr(reinterpret_cast<uptr>(other.data()));line.writeBackIfNeeded();CHECK(other[0]==0x39);expect(g,0,1);CHECK(g.report().accepted==0);});
 run([](auto& g){seed(0x5040);writebackCache();CHECK(ram[0x5040]==0x39&&ram[0x5000]==0xa5&&ram[0x5080]==0xa5);expect(g,0,1);});
 run([](auto& g){seed(0x3000);writebackCache();CHECK(ram[0x3000]==0x39);expect(g,0,1);},false);
}
void read_tests(){
 run([](auto& g){CHECK(readCache32(0x1000,true)==0xa5a5a5a5);CHECK(readCache32(0x1000,true)==0xa5a5a5a5);expect(g,0,0);});
 run([](auto& g){seed(0x3000);CHECK(readCache32(0x1000,true)==0xa5a5a5a5);CHECK(ram[0x3000]==0x39);expect(g,0,1,LifetimeReason::protected_write);});
 run([](auto& g){seed(0x3000,0,false);CHECK(readCache32(0x1000,true)==0xa5a5a5a5);expect(g,0,0);});
 run([](auto& g){CHECK(readCache32(0x7000,false)==0);expect(g,0,0);});
 run([](auto& g){before_cache();writeCache32(0x1000,42,true);CHECK(readCache32(0x9000,true)==42);int way=0;CHECK(findInCache(cache.sets[0],reinterpret_cast<uptr>(ram.data()+0x5000),&way));writebackCache();expect(g,1,1,LifetimeReason::lost);});
 run([](auto& g){seed(0x3000,0);seed(0x6000,1);cache.sets[0].tags[0].setLocked();CHECK(readCache32(0x1000,true)==0xa5a5a5a5);CHECK(ram[0x6000]==0x39&&ram[0x3000]==0xa5);expect(g,0,1);});
}
void instruction_tests(){
 for(unsigned instruction:{0x1au,0x18u,0x1cu,0x16u,0x11u,0x10u,0x13u,0x12u,0x14u,0x7u,0xcu,0x0u})run([=](auto& g){
  seed(0x3000);cpuRegs.GPR.r[0].UL[0]=0x3000;cpuRegs.CP0.n.TagLo=0x11223344;op=instruction;
  before_cache();R5900::Interpreter::OpcodeImpl::CACHE();
  const bool wrote=instruction==0x18||instruction==0x1c||instruction==0x10||instruction==0x14;
  CHECK(ram[0x3000]==(wrote?0x39:0xa5));
  if(instruction==0x13)CHECK(*reinterpret_cast<u32*>(cache.sets[0].data[0].bytes)==0x11223344);
  if(instruction==0x11)CHECK(cpuRegs.CP0.n.TagLo==0x39393939);
  if(instruction==0x1a||instruction==0x18||instruction==0x16||instruction==0x14)CHECK(!cache.sets[0].tags[0].isValid());
  expect(g,1,wrote?1:0,LifetimeReason::lost);
 });
 run([](auto& g){op=0x18;cpuRegs.GPR.r[0].UL[0]=0x1000;before_cache();R5900::Interpreter::OpcodeImpl::CACHE();expect(g,1,0,LifetimeReason::lost);});
 run([](auto& g){seed(0x3000);before_cache();resetCache();CHECK(!cache.sets[0].tags[0].isValid());CHECK(ram[0x3000]==0xa5);expect(g,1,0,LifetimeReason::lost);});
}
void jit_tests(){
 for(unsigned mode=0;mode<4;++mode)run([=](auto& g){eeRecNeedsReset=mode&1;jump_result=(mode&2)?1:0;expect_jit_barrier=true;recExecute();CHECK(!eeCpuExecuting&&!eeRecNeedsReset);CHECK(resets==(mode&1));CHECK(entries==((mode&2)?0u:1u));CHECK(prints==1);CHECK(ram[0x3000]==0xa5);expect(g,1,0,LifetimeReason::lost);});
 run([](auto& g){expect_jit_barrier=true;recExecute();recExecute();CHECK(entries==2);expect(g,2,0,LifetimeReason::lost);});
 run([](auto& g){recExecute();CHECK(entries==1);expect(g,1,0);},false);
 // Explicit negative scope: entering a preexisting callback directly bypasses
 // recExecute. An entry-only barrier cannot authorize mid-block arming.
 run([](auto& g){eeCpuExecuting=true;preexisting_compiled_callback();eeCpuExecuting=false;CHECK(entries==1);expect(g,0,0);});
}
int main(){width_tests<u8>();width_tests<u16>();width_tests<u32>();width_tests<u64>();width_tests<u128>();writeback_tests();read_tests();instruction_tests();jit_tests();
 CHECK(cases==70);
 std::printf("{\"cases\":%u,\"effects_digest\":\"%016llx\",\"result\":\"PASS\"}\n",cases,static_cast<unsigned long long>(digest));
}
