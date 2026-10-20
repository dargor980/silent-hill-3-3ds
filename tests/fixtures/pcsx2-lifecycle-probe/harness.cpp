// Own fixtures. Provider function bodies are exact, private .inc files.
#include "check.hpp"
#include "sh3_observer/physical_writes.hpp"
#include <algorithm>
#include <array>
#include <atomic>
#include <cstdint>
#include <cstdio>
#include <cstring>
#include <memory>
#include <mutex>
#include <string>
#include <utility>
#include <vector>
using namespace sh3::observer;
using u8=std::uint8_t;using u32=std::uint32_t;using u64=std::uint64_t;using s64=std::int64_t;using uptr=std::uintptr_t;using sptr=std::intptr_t;using vtlbHandler=u32;
struct {u64 cycle=1001;}cpuRegs;
struct alignas(4096) EEVM_MemoryAllocMess {u8 Main[65536]{};alignas(4096)u8 Scratch[4096]{};}memory;
EEVM_MemoryAllocMess* eeMem=&memory;
struct Logger{template<class...T>void WriteLn(T...){}template<class...T>void Error(T...){}}Console,DevCon;
constexpr int Color_StrongBlue=0,Color_Blue=1;
#define verify(x) CHECK(x)
#define pxAssume(x) CHECK(x)
#define pxAssert(x) CHECK(x)
#define pxAssertRel(x,...) CHECK(x)
LifetimeGuard* guard_ptr=nullptr;bool connected=true,require_notice=false;
std::vector<unsigned> order;unsigned notices=0,cases=0;u64 starting_epoch=0,first_hash=0;
void effect(unsigned id){
#ifdef SH3_ENABLE_OBSERVER
 if(connected&&require_notice){CHECK(guard_ptr->report().state==LifetimeState::failed);CHECK(host_epoch()>starting_epoch);}
#endif
 order.push_back(id);
}
struct VTLBPhysical {uptr value=0;bool special=true;static VTLBPhysical fromHandler(u32 h){return {h,true};}static VTLBPhysical fromPointer(sptr p){return {static_cast<uptr>(p),false};}};
struct VTLBVirtual {uptr value=0;bool special=true;VTLBVirtual()=default;VTLBVirtual(VTLBPhysical p,u32 pa,u32 va):value(p.special?p.value:p.value+(pa&4095)-va),special(p.special){}static VTLBVirtual fromPointer(uptr p,u32 v){VTLBVirtual r;r.value=p-v;r.special=false;return r;}bool isHandler(u32)const{return special;}uptr assumePtr(u32 a)const{return value+a;}};
constexpr u32 VTLB_PAGE_BITS=12,VTLB_PAGE_MASK=4095,VTLB_PAGE_SIZE=4096,VTLB_PMAP_SZ=65536,VTLB_VMAP_ITEMS=16;
std::array<VTLBVirtual,16> virtual_map;std::array<u32,16> physical_map;
struct {std::array<VTLBPhysical,16> pmap;VTLBVirtual* vmap=virtual_map.data();u32* ppmap=physical_map.data();uptr fastmem_base=1;}vtlbdata;
constexpr u32 UnmappedPhyHandler=31,UnmappedVirtHandler=32;
bool fastmem=false,recompiler=false;
#define CHECK_FASTMEM fastmem
#define CHECK_EEREC recompiler
namespace Ps2MemSize{constexpr u32 Scratch=4096;}
namespace HostMemoryMap{constexpr u32 EEmemOffset=0;}
struct PageProtectionMode{PageProtectionMode& Read(){return *this;}PageProtectionMode& Write(){return *this;}};
std::vector<std::array<u32,2>> fast_created,fast_removed;
std::vector<unsigned> s_fastmem_backpatch_info,s_fastmem_faulting_pcs,s_fastmem_physical_mapping,s_fastmem_virtual_mapping;
std::unique_ptr<int> s_fastmem_area;
bool vtlb_GetMainMemoryOffset(u32 p,u32* offset,u32* size,PageProtectionMode*){*offset=p;*size=4096;return p<32768;}
bool vtlb_GetMainMemoryOffsetFromPtr(uptr p,u32* offset,u32* size,PageProtectionMode*){auto b=reinterpret_cast<uptr>(memory.Main);if(p<b||p>=b+sizeof(memory.Main))return false;*offset=static_cast<u32>(p-b);*size=4096;return true;}
void vtlb_CreateFastmemMapping(u32 a,u32 o,const PageProtectionMode&){effect(10);fast_created.push_back({a,o});}
void vtlb_RemoveFastmemMapping(u32 a){effect(11);fast_removed.push_back({a,4096});}
void vtlb_RemoveFastmemMappings(u32 a,u32 size){effect(12);fast_removed.push_back({a,size});}
void vtlb_RemoveFastmemMappings(){effect(13);fast_removed.push_back({0,0});}
void vtlb_ClearLoadStoreInfo(){effect(14);}
struct tlbs{u32 value;};tlbs tlb[48]{},s_tlb_backup[48]{};
void UnmapTLB(const tlbs&,int){effect(15);}
u64 state_hash();
namespace sh3::observer{void harness_lifecycle(LifetimeKind,u64)noexcept;}
#define before_lifecycle harness_lifecycle
#include "map-handler.inc"
#include "map-block.inc"
#include "mirror.inc"
#include "vmap.inc"
#include "vmap-buffer.inc"
#include "unmap.inc"
#include "tlb-reset.inc"
#include "tlb-shutdown.inc"
#include "fastmem-reset.inc"
#include "core-free.inc"
bool allocation_ok=true,core_allocation_ok=true;
bool AllocateMemoryMap(){effect(20);return allocation_ok;}void ReleaseMemoryMap(){effect(21);}
void iopMemAlloc(){effect(22);}void vuMemAllocate(){effect(23);}bool vtlb_Core_Alloc(){effect(24);return core_allocation_ok;}
void vuMemRelease(){effect(25);}void iopMemRelease(){effect(26);}
// Deliberate reset dependencies: memReset/cpuReset bodies are compiled separately, not executed here.
void memReset(){effect(27);std::memset(memory.Main,0,sizeof(memory.Main));}
void iopMemReset(){effect(28);}void vuMemReset(){effect(29);}
namespace SysMemory{void* GetEEMem(){return &memory;}bool Allocate();void Release();void Reset();}
#include "memory-allocate.inc"
#include "memory-release.inc"
#include "system-allocate.inc"
#include "system-release.inc"
#include "system-reset.inc"
bool vu_thread=false;
#define THREAD_VU1 vu_thread
struct {void WaitVU(){effect(30);}void Reset(){effect(31);}}vu1Thread;
namespace MTGS{void WaitGS(bool=true){effect(32);}void PresentCurrentFrame(){effect(33);}}
void mmap_ResetBlockTracking(){effect(34);}
enum class VMState{Paused,Running,Resetting,Stopping};std::atomic<VMState>s_state{VMState::Paused};
struct Pcsx2Config{struct{bool ExtraMemory=false;}Cpu;unsigned value=7;void CopyRuntimeConfig(const Pcsx2Config& p){Cpu=p.Cpu;}}EmuConfig;
namespace VMManager{bool HasValidVM(){return true;}bool HasValidOrInitializingVM(){return true;}VMState GetState(){return s_state.load();}void ApplySettings();void ApplyCoreSettings();void Reset();void Execute();namespace Internal{void ClearCPUExecutionCaches(){effect(35);}}}
void LoadSettings(){effect(36);EmuConfig.value=11;}void CheckForConfigChanges(const Pcsx2Config&){effect(37);}
struct FPControlRegister{static int GetDefault(){return 0;}};struct FPControlRegisterBackup{explicit FPControlRegisterBackup(int){}};
namespace Host{std::mutex settings_mutex;std::unique_lock<std::mutex> GetSettingsLock(){return std::unique_lock<std::mutex>(settings_mutex);}int* GetSettingsInterface(){static int value=0;return &value;}}
void LoadCoreSettings(int){effect(38);EmuConfig.value=12;}void WarnAboutUnsafeSettings(){}void ApplyGameFixes(){effect(39);}
#include "settings.inc"
#include "core-settings.inc"
bool confirm_reset=true,hardcore=false,dump=false;u32 s_current_crc=0;
namespace Achievements{bool ConfirmSystemReset(){return confirm_reset;}bool ResetHardcoreMode(bool){return hardcore;}void ResetClient(){effect(40);}}
namespace GSDumpReplayer{bool IsReplayingDump(){return dump;}}
void ClearELFInfo(){effect(41);s_current_crc=0;}void HandleELFChange(bool){effect(42);}
void memSetExtraMemMode(bool){effect(43);}void memBindConditionalHandlers(){effect(44);}
void cpuReset(){effect(45);cpuRegs.cycle=0;}void hwReset(){effect(46);}void ResetFrameLimiter(){effect(47);}
struct {bool active=false;bool isActive(){return active;}void handleReset(){effect(48);}}g_InputRecording;
#include "reset.inc"
bool s_cpu_implementation_changed=false;void UpdateCPUImplementations(){effect(49);}
struct CPU {void Execute(){effect(50);}}cpu;CPU* Cpu=&cpu;
#include "execute.inc"
#include "preload.inc"
// ZIP and loader dependencies inject errors without using real game files.
struct Error{std::string message;bool IsValid()const{return !message.empty();}static void SetString(Error* e,std::string s){e->message=std::move(s);}};
namespace fmt{template<class...T>std::string format(const char*,T...){return "synthetic load error";}}
struct zip_t{};struct zip_error_t{};struct ZipHandle{zip_t* p=nullptr;explicit operator bool()const{return p!=nullptr;}zip_t* get()const{return p;}};
zip_t fake_zip;constexpr int ZIP_RDONLY=0,ZIP_ER_NOENT=1;
bool open_ok=true,version_ok=true,required_ok=true,optional_present=true,internal_ok=true,entry_ok=true,entry_open_ok=true;
ZipHandle zip_open_managed(const char*,int,zip_error_t*){return {open_ok?&fake_zip:nullptr};}
const char* zip_error_strerror(zip_error_t*){return "synthetic";}int zip_error_code_zip(zip_error_t*){return ZIP_ER_NOENT;}
bool CheckVersion(const std::string&,zip_t*,Error*){return version_ok;}
constexpr const char* EntryFilename_InternalStructures="own-internal";
struct Entry{bool required;const char* name;bool IsRequired()const{return required;}const char* GetFilename()const{return name;}bool FreezeIn(zip_t* z){effect(52);memory.Main[8]=z?42:0;return entry_ok;}};
Entry required_entry{true,"own-required"},optional_entry{false,"own-optional"};Entry* SavestateEntries[]={&required_entry,&optional_entry};
s64 CheckFileExistsInState(zip_t*,const char* name,bool required){if(!required_ok&&required)return -1;if(std::strcmp(name,EntryFilename_InternalStructures)==0)return 0;return required?1:(optional_present?2:-1);}
ZipHandle zip_fopen_index_managed(zip_t*,s64,int){return {entry_open_ok?&fake_zip:nullptr};}
bool LoadInternalStructuresState(zip_t*,s64,Error*){effect(51);memory.Main[0]=77;cpuRegs.cycle=17;return internal_ok;}
void PostLoadPrep(){effect(53);}
#include "unzip.inc"
#undef before_lifecycle
namespace sh3::observer{
void harness_lifecycle(LifetimeKind kind,u64 cycle)noexcept{if(notices==0)first_hash=state_hash();++notices;before_lifecycle(kind,cycle);}
}
u64 addhash(u64 h,u64 v){for(unsigned n=0;n<8;++n){h^=(v>>(8*n))&255;h*=1099511628211ULL;}return h;}
u64 normalized(uptr p){auto b=reinterpret_cast<uptr>(&memory);return p>=b-65536&&p<b+sizeof(memory)+65536?p-b:p;}
u64 state_hash(){u64 h=0;for(auto v:memory.Main)h=addhash(h,v);for(auto v:memory.Scratch)h=addhash(h,v);for(const auto& p:vtlbdata.pmap){h=addhash(h,p.special);h=addhash(h,normalized(p.value));}for(const auto& p:virtual_map){h=addhash(h,p.special);h=addhash(h,normalized(p.value));}for(auto v:physical_map)h=addhash(h,v);h=addhash(h,eeMem!=nullptr);h=addhash(h,vtlbdata.vmap!=nullptr);h=addhash(h,vtlbdata.ppmap!=nullptr);h=addhash(h,cpuRegs.cycle);h=addhash(h,static_cast<unsigned>(s_state.load()));h=addhash(h,EmuConfig.value);return h;}
u64 digest=14695981039346656037ULL;
LifetimePlan plan(){return {{{{1}},host_epoch(),100,1000},{0x1000,0x2000,0x3000,0x4000},1000};}
template<class F>void run(F test,bool bind=true){
 std::memset(memory.Main,0xa5,sizeof(memory.Main));std::memset(memory.Scratch,0xa5,sizeof(memory.Scratch));eeMem=&memory;cpuRegs.cycle=1001;
 virtual_map.fill({});physical_map.fill(0);vtlbdata.pmap.fill({});vtlbdata.vmap=virtual_map.data();vtlbdata.ppmap=physical_map.data();vtlbdata.fastmem_base=1;
 fast_created.clear();fast_removed.clear();s_fastmem_backpatch_info={1};s_fastmem_faulting_pcs={2};s_fastmem_physical_mapping={3};s_fastmem_virtual_mapping={4};s_fastmem_area=std::make_unique<int>(1);
 for(unsigned i=0;i<48;++i){tlb[i].value=i;s_tlb_backup[i].value=0;}
 notices=0;first_hash=0;order.clear();starting_epoch=host_epoch();connected=bind;require_notice=false;fastmem=recompiler=vu_thread=false;
 allocation_ok=core_allocation_ok=confirm_reset=true;hardcore=dump=false;s_current_crc=0;g_InputRecording.active=false;s_state=VMState::Paused;EmuConfig={};s_cpu_implementation_changed=false;
 open_ok=version_ok=required_ok=optional_present=internal_ok=entry_ok=entry_open_ok=true;
 LifetimeGuard guard;CHECK(guard.arm(plan()));guard_ptr=&guard;PhysicalWrites bridge(guard,reinterpret_cast<uptr>(memory.Main));
 if(bind){WriteBinding binding(bridge);CHECK(binding.connected());test(guard);}else test(guard);
 digest=addhash(digest,state_hash());for(auto id:order)digest=addhash(digest,id);for(auto m:fast_created)for(auto v:m)digest=addhash(digest,v);for(auto m:fast_removed)for(auto v:m)digest=addhash(digest,v);
 for(auto t:s_tlb_backup)digest=addhash(digest,t.value);digest=addhash(digest,vtlbdata.fastmem_base);digest=addhash(digest,s_fastmem_backpatch_info.size());digest=addhash(digest,s_fastmem_faulting_pcs.size());digest=addhash(digest,s_fastmem_area!=nullptr);++cases;
}
void expect(LifetimeGuard& g,unsigned count,LifetimeReason reason,u64 prior){
#ifdef SH3_ENABLE_OBSERVER
 CHECK(notices==count&&host_epoch()==starting_epoch+count);if(count)CHECK(first_hash==prior);
 if(connected&&count){CHECK(g.report().state==LifetimeState::failed&&g.report().reason==reason);return;}
#else
 (void)count;(void)reason;(void)prior;CHECK(notices==0&&host_epoch()==starting_epoch);
#endif
 CHECK(g.report().state==LifetimeState::armed);
}
void map_tests(){
 run([](auto& g){auto before=state_hash();require_notice=true;vtlb_MapHandler(7,0x2000,8192);CHECK(vtlbdata.pmap[2].special&&vtlbdata.pmap[3].value==7);expect(g,1,LifetimeReason::remap,before);});
 for(u32 block:{0u,4096u})run([=](auto& g){auto before=state_hash();require_notice=true;vtlb_MapBlock(memory.Main,0x2000,8192,block);CHECK(vtlbdata.pmap[3].value==reinterpret_cast<uptr>(memory.Main)+(block?0:4096));expect(g,1,LifetimeReason::remap,before);});
 run([](auto& g){vtlbdata.pmap[1]=VTLBPhysical::fromHandler(9);auto before=state_hash();require_notice=true;vtlb_Mirror(0x1000,0x3000,4096);CHECK(vtlbdata.pmap[3].value==9);expect(g,1,LifetimeReason::remap,before);});
 for(unsigned mode=0;mode<4;++mode)run([=](auto& g){fastmem=mode&1;vtlbdata.ppmap=mode&2?nullptr:physical_map.data();vtlbdata.pmap[2]=VTLBPhysical::fromPointer(reinterpret_cast<sptr>(memory.Main));auto before=state_hash();require_notice=true;vtlb_VMap(0x3000,0x2000,8192);CHECK(!virtual_map[3].special&&virtual_map[4].special);expect(g,1,LifetimeReason::remap,before);});
 run([](auto& g){fastmem=true;auto before=state_hash();require_notice=true;vtlb_VMap(0x3000,0x10000,4096);CHECK(virtual_map[3].special&&fast_removed.size()==1);expect(g,1,LifetimeReason::remap,before);});
 for(unsigned mode=0;mode<3;++mode)run([=](auto& g){fastmem=mode!=0;void* ptr=mode==2?memory.Scratch:memory.Main;auto before=state_hash();require_notice=true;vtlb_VMapBuffer(0x2000,ptr,4096);CHECK(virtual_map[2].assumePtr(0x2000)==reinterpret_cast<uptr>(ptr));expect(g,1,LifetimeReason::remap,before);});
 run([](auto& g){auto before=state_hash();require_notice=true;vtlb_VMapUnmap(0x3000,8192);CHECK(virtual_map[3].special&&virtual_map[4].special);expect(g,1,LifetimeReason::remap,before);});
 run([](auto& g){auto before=state_hash();vtlb_MapHandler(7,0x2000,4096);vtlb_MapHandler(7,0x2000,4096);expect(g,2,LifetimeReason::remap,before);});
 run([](auto& g){auto before=state_hash();vtlb_VMapUnmap(0x3000,4096);expect(g,1,LifetimeReason::remap,before);},false);
}
void tlb_tests(){
 run([](auto& g){auto before=state_hash();require_notice=true;vtlb_Reset();CHECK(order.size()==49);expect(g,1,LifetimeReason::reset,before);});
 run([](auto& g){auto before=state_hash();require_notice=true;vtlb_Shutdown();CHECK(s_fastmem_backpatch_info.empty()&&s_fastmem_faulting_pcs.empty());expect(g,1,LifetimeReason::shutdown,before);});
 for(unsigned mode=0;mode<4;++mode)run([=](auto& g){fastmem=mode!=0;recompiler=mode>1;if(mode==2)vtlbdata.vmap=nullptr;virtual_map[1]=VTLBVirtual::fromPointer(reinterpret_cast<uptr>(memory.Main),0x1000);auto before=state_hash();require_notice=true;vtlb_ResetFastmem();CHECK(fast_created.size()==(mode==3?1:0));expect(g,1,LifetimeReason::remap,before);});
 run([](auto& g){auto before=state_hash();require_notice=true;vtlb_Core_Free();CHECK(!vtlbdata.vmap&&!vtlbdata.ppmap&&!s_fastmem_area&&vtlbdata.fastmem_base==0);expect(g,1,LifetimeReason::shutdown,before);});
}
void memory_tests(){
 run([](auto& g){eeMem=nullptr;auto before=state_hash();memAllocate();CHECK(eeMem==&memory);expect(g,1,LifetimeReason::remap,before);});
 for(bool bind:{true,false})run([](auto& g){auto before=state_hash();memRelease();CHECK(eeMem==nullptr);expect(g,1,LifetimeReason::shutdown,before);},bind);
 for(unsigned mode=0;mode<3;++mode)run([=](auto& g){allocation_ok=mode!=1;core_allocation_ok=mode!=2;eeMem=nullptr;auto before=state_hash();require_notice=true;CHECK(SysMemory::Allocate()==(mode==0));CHECK((eeMem!=nullptr)==allocation_ok);expect(g,mode==1?1:2,LifetimeReason::remap,before);});
 run([](auto& g){auto before=state_hash();require_notice=true;SysMemory::Release();CHECK(!eeMem&&!vtlbdata.vmap);expect(g,3,LifetimeReason::shutdown,before);});
}
void execution_tests(){
 for(bool change:{false,true})run([=](auto& g){s_cpu_implementation_changed=change;auto before=state_hash();require_notice=change;VMManager::Execute();CHECK(!s_cpu_implementation_changed&&order.back()==50);expect(g,change?2:0,LifetimeReason::settings,before);});
 for(unsigned mode=0;mode<4;++mode)run([=](auto& g){s_state=mode&1?VMState::Running:VMState::Paused;vu_thread=true;auto before=state_hash();require_notice=true;if(mode&2)VMManager::ApplyCoreSettings();else VMManager::ApplySettings();CHECK(EmuConfig.value==(mode&2?12u:11u));expect(g,1,LifetimeReason::settings,before);});
 run([](auto& g){auto before=state_hash();require_notice=true;VMManager::ApplySettings();VMManager::ApplySettings();expect(g,2,LifetimeReason::settings,before);});
 run([](auto& g){s_state=VMState::Running;auto before=state_hash();VMManager::Reset();CHECK(s_state==VMState::Resetting&&order.empty());expect(g,1,LifetimeReason::reset,before);});
 run([](auto& g){confirm_reset=false;auto before=state_hash();VMManager::Reset();CHECK(order.empty());expect(g,0,LifetimeReason::none,before);});
 for(unsigned mode=0;mode<4;++mode)run([=](auto& g){hardcore=mode&1;dump=mode&2;g_InputRecording.active=true;s_current_crc=7;s_state=VMState::Resetting;auto before=state_hash();require_notice=true;VMManager::Reset();CHECK(cpuRegs.cycle==0&&memory.Main[0]==0&&s_state==VMState::Running);expect(g,hardcore&&!dump?2:1,LifetimeReason::reset,before);});
}
void restore_tests(){
 for(bool vu:{false,true})run([=](auto& g){vu_thread=vu;auto before=state_hash();require_notice=true;PreLoadPrep();CHECK(s_tlb_backup[47].value==47);expect(g,1,LifetimeReason::restore,before);});
 for(unsigned mode=0;mode<8;++mode)run([=](auto& g){open_ok=mode!=1;version_ok=mode!=2;required_ok=mode!=3;internal_ok=mode!=4;entry_open_ok=mode!=5;entry_ok=mode!=6;optional_present=mode!=7;auto before=state_hash();require_notice=mode==0||mode>=4;Error error;bool ok=SaveState_UnzipFromDisk("own-state",&error);CHECK(ok==(mode==0||mode==7));unsigned count=mode>=1&&mode<=3?0:mode>=4&&mode<=6?2:1;expect(g,count,LifetimeReason::restore,before);if(mode>=4&&mode<=6)CHECK(cpuRegs.cycle==0&&memory.Main[0]==0);});
 run([](auto& g){auto before=state_hash();require_notice=true;Error e;CHECK(SaveState_UnzipFromDisk("own-state",&e));CHECK(SaveState_UnzipFromDisk("own-state",&e));expect(g,2,LifetimeReason::restore,before);});
 run([](auto& g){auto before=state_hash();Error e;CHECK(SaveState_UnzipFromDisk("own-state",&e));expect(g,1,LifetimeReason::restore,before);},false);
}
int main(){map_tests();tlb_tests();memory_tests();execution_tests();restore_tests();std::printf("{\"cases\":%u,\"effects_digest\":\"%016llx\",\"result\":\"PASS\"}\n",cases,static_cast<unsigned long long>(digest));}
