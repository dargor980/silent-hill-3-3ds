#include "sh3_observer/macos_platform_origin.hpp"
#include "sh3_observer/macos_image_identity.hpp"
#include "check.hpp"
#include <algorithm>
#include <cerrno>
#include <cstring>
#include <dlfcn.h>
#include <libproc.h>
#include <mach/mach.h>
#include <mach/mach_vm.h>
#include <mach-o/dyld.h>
#include <mach-o/loader.h>
#include <string>
#include <sys/wait.h>
#include <sys/proc_info.h>
#include <unistd.h>
using namespace sh3::observer;
namespace {
struct Api {
  int pid{42}, pid_calls{}, change_pid{}, create_calls{}, dispose_calls{}, snapshots{}, releases{}, cache_calls{}, image_calls{}, segment_calls{};
  int fault{}, fault_pass{2}, shape{}; std::size_t entries{2};
  bool reverse{};
  int preflights{}, fail_preflight{};
} api;
int pid() { ++api.pid_calls; return api.change_pid && api.pid_calls >= api.change_pid ? 43 : api.pid; }
dyld_process_s* create() { ++api.create_calls; return api.fault == 1 ? nullptr : reinterpret_cast<dyld_process_s*>(1); }
void dispose(dyld_process_s* p) { CHECK(p == reinterpret_cast<dyld_process_s*>(1)); CHECK(api.releases == api.snapshots-(api.fault == 2 ? 1 : 0)); ++api.dispose_calls; }
dyld_process_snapshot_s* snapshot(dyld_process_s* p,kern_return_t* status) {
  CHECK(p == reinterpret_cast<dyld_process_s*>(1)); ++api.snapshots;
  const bool fault = api.snapshots == api.fault_pass;
  *status = fault && api.fault == 3 ? KERN_FAILURE : KERN_SUCCESS;
  return fault && api.fault == 2 ? nullptr : reinterpret_cast<dyld_process_snapshot_s*>(2);
}
void release(dyld_process_snapshot_s* p) { CHECK(p == reinterpret_cast<dyld_process_snapshot_s*>(2)); ++api.releases; }
dyld_shared_cache_s* cache(dyld_process_snapshot_s* p) {
  CHECK(p == reinterpret_cast<dyld_process_snapshot_s*>(2)); ++api.cache_calls;
  return api.fault == 4 && api.snapshots == api.fault_pass ? nullptr : reinterpret_cast<dyld_shared_cache_s*>(3);
}
std::uint64_t base(dyld_shared_cache_s*) { return api.fault == 5 ? 0 : api.fault == 7 ? UINT64_MAX-1 : 0x8000; }
std::uint64_t size(dyld_shared_cache_s*) { return api.fault == 6 ? 0 : platform_cache_capacity*4096ULL; }
void uuid(dyld_shared_cache_s*,uuid_t* out) { std::memset(out,api.fault == 8 ? 0 : 9,sizeof(uuid_t)); }
void images(dyld_shared_cache_s*,void(^block)(dyld_image_s*)) {
  ++api.image_calls;
  for (std::size_t n=0;n<api.entries;++n) {
    const auto index = api.reverse ? api.entries-n : n+1;
    block(reinterpret_cast<dyld_image_s*>(api.shape == 1 ? 0 : index));
  }
}
bool segments(dyld_image_s* p,void(^block)(const char*,std::uint64_t,std::uint64_t,int)) {
  ++api.segment_calls; auto address = 0x8000+(reinterpret_cast<std::uintptr_t>(p)-1)*4096;
  if (api.shape == 2) return false;
  if (api.shape == 3) return true;
  if (api.shape == 4) address = 0x8000;
  if (api.shape == 5) address = 0x7fff;
  if (api.shape == 6) address = 0x8000+size(nullptr);
  const auto length = api.shape == 7 ? 0 : api.shape == 8 ? UINT64_MAX : 4096;
  block(api.shape == 9 ? nullptr : "__TEXT",address,length,api.shape == 10 ? 0 : 1);
  if (api.shape == 11) block("__TEXT",address,4096,1);
  for (int i=1;i<(api.shape == 12 ? 257 : api.shape == 13 ? 256 : 1);++i) block("__DATA",address,4096,3);
  return true;
}
bool preflight() {return ++api.preflights!=api.fail_preflight;}
MacOSCacheCalls calls() { return {pid,create,dispose,snapshot,release,cache,images,segments,uuid,base,size,preflight}; }
struct Events final : ImageSnapshotSource {
  ImageSnapshot value{}; int reads{}, failure_at{}, change_at{}, invalid{}; bool reverse{};
  Events() { value.count=2; value.revision=7; value.addresses[0]=0x1000; value.addresses[1]=0x8000; }
  bool read(ImageSnapshot& out) noexcept override {
    ++reads; out=value;
    if (change_at && reads>=change_at) ++out.revision;
    if (invalid==1) out.count=0; if (invalid==2) out.count=image_capacity+1;
    if (invalid==3) out.revision=0; if (invalid==4) out.revision=UINT64_MAX;
    if (invalid==5) out.addresses[0]=0; if (invalid==6) out.addresses[1]=out.addresses[0];
    if (reverse && reads%2) std::swap(out.addresses[0],out.addresses[1]);
    return reads!=failure_at;
  }
};
struct Maps final : MappingSource {
  int reads{}, invalid{}; bool ok{true}; Events* change{};
  bool read(std::uintptr_t address,MappedFile& out) noexcept override {
    ++reads; out={address,4096,0,{1,2,4096,3,4,5,6}};
    if (invalid==1) ++out.address; if (invalid==2) out.size=0;
    if (invalid==3) out.size=UINT64_MAX; if (invalid==4) out.offset=1;
    if (invalid==5) out.file.inode=0; if (change) ++change->value.revision;
    return ok;
  }
};
bool empty(const ImageOrigin& o) { return o.kind==ImageOriginKind::unknown && !o.application.address && !o.application.size && !o.application.offset && same_file(o.application.file,{}) && !o.cache.address && !o.cache.base && !o.cache.size && o.cache.uuid==CacheUuid{}; }
void rejected(MacOSPlatformOrigins& source,Events& e,Maps& m,PlatformOriginFailure expected,std::uintptr_t address=0x1000) {
  ImageOrigin o{}; o.cache.size=99; CHECK(!source.read(address,o) && empty(o)); CHECK(source.failure()==expected);
  const auto p=api.pid_calls,er=e.reads,mr=m.reads; o.cache.size=99;
  CHECK(!source.read(0x8000,o) && empty(o)); CHECK(api.pid_calls==p && e.reads==er && m.reads==mr && source.catalog_size()==0);
}
void synthetic(const std::string& name) {
  if (name=="missing_api") {
    for (int i=0;i<12;++i) {
      api={}; auto c=calls();
      if(i==0)c.pid=nullptr;if(i==1)c.create=nullptr;if(i==2)c.dispose=nullptr;if(i==3)c.snapshot=nullptr;
      if(i==4)c.release=nullptr;if(i==5)c.cache=nullptr;if(i==6)c.images=nullptr;if(i==7)c.segments=nullptr;
      if(i==8)c.uuid=nullptr;if(i==9)c.base=nullptr;if(i==10)c.size=nullptr;
      if(i==11)c.preflight=nullptr;
      Events e;Maps m;MacOSPlatformOrigins source(e,m,c);rejected(source,e,m,PlatformOriginFailure::api);CHECK(!api.create_calls&&!api.pid_calls);
    } return;
  }
  if (name=="preflight") {
    for(int at=1;at<=3;++at) {
      api={};api.fail_preflight=at;Events e;Maps m;MacOSPlatformOrigins source(e,m,calls());
      rejected(source,e,m,PlatformOriginFailure::preflight);
      CHECK(api.create_calls==(at==1?0:1)&&api.snapshots==(at==3?1:0));
      CHECK(api.dispose_calls==api.create_calls&&api.releases==api.snapshots);
    }return;
  }
  if (name=="prepare_errors") {
    for (int pass=1;pass<=2;++pass) {
      for(int f=1;f<=8;++f) {
        api={};api.fault=f;api.fault_pass=pass;Events e;Maps m;MacOSPlatformOrigins source(e,m,calls());
        auto wanted=f==1?PlatformOriginFailure::process:f<=3?PlatformOriginFailure::snapshot:PlatformOriginFailure::cache;
        rejected(source,e,m,wanted);CHECK(api.dispose_calls==(f==1?0:1));
      }
    }
    return;
  }
  if (name=="invalid_catalog") {
    for(int shape=1;shape<=12;++shape) {api={};api.shape=shape;Events e;Maps m;MacOSPlatformOrigins source(e,m,calls());rejected(source,e,m,PlatformOriginFailure::catalog);CHECK(api.releases==2&&api.dispose_calls==1);}
    return;
  }
  if (name=="catalog_limits") {
    for(auto count:{std::size_t(0),platform_cache_capacity,platform_cache_capacity+1}) {
      api={};api.entries=count;api.reverse=count==platform_cache_capacity;Events e;Maps m;MacOSPlatformOrigins source(e,m,calls());
      if(count!=platform_cache_capacity)rejected(source,e,m,PlatformOriginFailure::catalog);
      else {ImageOrigin o{};CHECK(source.catalog_size()==count&&source.read(0x8000,o)&&o.kind==ImageOriginKind::platform_cache);}
    } return;
  }
  if (name=="loader_errors") {
    for(int at=1;at<=4;++at){api={};Events e;e.failure_at=at;Maps m;MacOSPlatformOrigins source(e,m,calls());rejected(source,e,m,PlatformOriginFailure::loader);}
    for(int invalid=1;invalid<=6;++invalid){api={};Events e;e.invalid=invalid;Maps m;MacOSPlatformOrigins source(e,m,calls());rejected(source,e,m,PlatformOriginFailure::loader);} return;
  }
  if (name=="pid_errors") {
    api={};api.pid=0;Events e;Maps m;MacOSPlatformOrigins source(e,m,calls());rejected(source,e,m,PlatformOriginFailure::process);CHECK(!api.create_calls);
    for(int at=2;at<=9;++at){api={};api.change_pid=at;Events e2;Maps m2;MacOSPlatformOrigins s(e2,m2,calls());rejected(s,e2,m2,PlatformOriginFailure::process);}return;
  }
  if (name=="loader_changes") {
    for(int at=2;at<=4;++at){api={};Events e;e.change_at=at;Maps m;MacOSPlatformOrigins source(e,m,calls());rejected(source,e,m,PlatformOriginFailure::changed);}
    for(int field=0;field<2;++field){api={};Events e;Maps m;MacOSPlatformOrigins source(e,m,calls());if(field==0)e.value.count=1;else e.value.addresses[0]=0x2000;rejected(source,e,m,PlatformOriginFailure::changed);}return;
  }
  if (name=="mapping_errors") {
    for(int invalid=0;invalid<=5;++invalid){api={};Events e;Maps m;m.invalid=invalid;m.ok=invalid!=0;MacOSPlatformOrigins source(e,m,calls());rejected(source,e,m,PlatformOriginFailure::mapping);}return;
  }
  api={};Events e;Maps m;
  if(name=="order"){e.reverse=true;api.reverse=true;api.shape=13;}
  if(name=="range_only")e.value.addresses[0]=0x8001;
  MacOSPlatformOrigins source(e,m,calls());CHECK(source.failure()==PlatformOriginFailure::none&&source.catalog_size()==2);
  CHECK(api.snapshots==2&&api.releases==2&&api.dispose_calls==1);
  if(name=="unknown"){rejected(source,e,m,PlatformOriginFailure::address,0x8001);return;}
  if(name=="unloaded"){rejected(source,e,m,PlatformOriginFailure::address,0x9000);return;}
  if(name=="zero"){rejected(source,e,m,PlatformOriginFailure::address,0);return;}
  if(name=="during_mapping"){m.change=&e;rejected(source,e,m,PlatformOriginFailure::changed);return;}
  if(name=="range_only"){ImageOrigin out{};CHECK(source.read(0x8001,out)&&out.kind==ImageOriginKind::application&&!out.cache.base);CHECK(m.reads==1);return;}
  CHECK(name=="stable"||name=="order");
  for(int n=0;n<2;++n){ImageOrigin o{};CHECK(source.read(0x8000,o)&&o.kind==ImageOriginKind::platform_cache&&o.cache.address==0x8000&&o.cache.base==0x8000&&o.cache.uuid[0]==9);CHECK(!o.application.address);CHECK(source.read(0x1000,o)&&o.kind==ImageOriginKind::application&&o.application.address==0x1000&&!o.cache.base);}
  CHECK(m.reads==2&&api.image_calls==1);
}
struct NativeEvents final : ImageSnapshotSource { bool read(ImageSnapshot& out) noexcept override {return MacOSImageEvents::read(out);} };
struct Library {
  void* handle{}; const mach_header_64* header{};
  explicit Library(const char* path) {handle=dlopen(path,RTLD_NOW|RTLD_LOCAL);CHECK(handle);auto sym=dlsym(handle,"sh3_image_fixture");CHECK(sym);Dl_info i{};CHECK(dladdr(sym,&i));header=static_cast<const mach_header_64*>(i.dli_fbase);CHECK(header&&header->magic==MH_MAGIC_64);}
  ~Library(){CHECK(dlclose(handle)==0);}
};
void native(const std::string& name,const char* fixture) {
  NativeEvents e;MacOSMappingSource m;
  if(name=="impostor") {
    CHECK(_dyld_shared_cache_contains_path("/usr/lib/libsqlite3.dylib"));Library lib(fixture);
    const auto page=static_cast<std::uint64_t>(sysconf(_SC_PAGESIZE));const auto address=reinterpret_cast<std::uintptr_t>(lib.header);const auto start=address-address%page;
    const auto original=lib.header->flags;CHECK(!(original&MH_DYLIB_IN_CACHE));
    MacOSPlatformOrigins source(e,m);ImageOrigin out{};CHECK(source.read(address,out)&&out.kind==ImageOriginKind::application);
    CHECK(mach_vm_protect(mach_task_self(),start,page,false,VM_PROT_READ|VM_PROT_WRITE|VM_PROT_COPY)==KERN_SUCCESS);
    auto writable=const_cast<mach_header_64*>(lib.header);writable->flags=original|MH_DYLIB_IN_CACHE;
    CHECK(source.read(address,out));CHECK(out.kind==ImageOriginKind::application&&out.application.address==address&&!out.cache.base);
    MacOSPlatformOrigins forged(e,m);CHECK(forged.failure()==PlatformOriginFailure::preflight);
    CHECK(!forged.read(address,out)&&empty(out));
    CHECK(lib.header->flags&MH_DYLIB_IN_CACHE);writable->flags=original;
    CHECK(mach_vm_protect(mach_task_self(),start,page,false,VM_PROT_READ|VM_PROT_EXECUTE)==KERN_SUCCESS);return;
  }
  MacOSPlatformOrigins source(e,m);CHECK(source.failure()==PlatformOriginFailure::none&&source.catalog_size()>0);
  if(name=="fork") {
    const auto child=fork();CHECK(child>=0);if(child==0){ImageOrigin out{};out.cache.size=99;CHECK(!source.read(1,out)&&empty(out)&&source.failure()==PlatformOriginFailure::process);_exit(0);}
    int status{};pid_t waited;do{waited=waitpid(child,&status,0);}while(waited<0&&errno==EINTR);CHECK(waited==child&&WIFEXITED(status)&&WEXITSTATUS(status)==0);return;
  }
  ImageSnapshot loaded{};CHECK(e.read(loaded));
  if(name=="cycle") { {Library lib(fixture);} ImageOrigin out{};CHECK(!source.read(loaded.addresses[0],out)&&empty(out)&&source.failure()==PlatformOriginFailure::changed);return; }
  CHECK(name=="native");std::size_t app{},platform{};
  for(std::size_t i=0;i<loaded.count;++i){
    ImageOrigin out{};
    if(!source.read(loaded.addresses[i],out)) {
      // This toolchain ships a universal ASan runtime. Its x86_64 header maps
      // at a nonzero file offset, outside PT03's current zero-offset scope.
      // Verify that exact counterexample; never waive it in the provider.
      const auto sanitizer=dlsym(RTLD_DEFAULT,"__asan_init");Dl_info info{};
      CHECK(sanitizer&&dladdr(sanitizer,&info)&&reinterpret_cast<std::uintptr_t>(info.dli_fbase)==loaded.addresses[i]);
      proc_regionwithpathinfo region{};
      CHECK(proc_pidinfo(getpid(),PROC_PIDREGIONPATHINFO,loaded.addresses[i],&region,sizeof(region))==sizeof(region));
      CHECK(region.prp_prinfo.pri_address==loaded.addresses[i]&&region.prp_prinfo.pri_size>0&&region.prp_prinfo.pri_offset>0);
      CHECK(source.failure()==PlatformOriginFailure::mapping&&empty(out));
      CHECK(!source.read(loaded.addresses[0],out)&&empty(out));
      std::printf("NATIVE_ASAN_OFFSET_REJECTED offset=%llu\n",static_cast<unsigned long long>(region.prp_prinfo.pri_offset));return;
    }
    if(out.kind==ImageOriginKind::platform_cache)++platform;else{CHECK(out.kind==ImageOriginKind::application);++app;}
  }
  CHECK(app>0&&platform>0&&app+platform==loaded.count);
}
}
int main(int argc,char** argv) {
  CHECK(argc==3);const std::string name=argv[1];
  if(name=="native"||name=="impostor"||name=="fork"||name=="cycle")native(name,argv[2]);else synthetic(name);
}
