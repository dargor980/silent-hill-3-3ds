#include "sh3_observer/macos_slice_binding.hpp"
#include "sh3_observer/macos_platform_origin.hpp"
#include "sh3_observer/macos_image_identity.hpp"
#include "macho_slice_fixture.hpp"
#include "check.hpp"
#include <dlfcn.h>
#include <filesystem>
#include <fstream>
#include <mach/mach.h>
#include <mach/mach_vm.h>
#include <sys/wait.h>
#include <unistd.h>
using namespace sh3::observer;
namespace fs=std::filesystem;
namespace {
std::string forced;int pid_calls{},change_pid_at{};
int pid(){return ++pid_calls==change_pid_at?getpid()+1:getpid();}
bool locate(std::uintptr_t,std::string& out){out=forced;return !out.empty();}
struct Events final:ImageSnapshotSource{bool read(ImageSnapshot& out)noexcept override{return MacOSImageEvents::read(out);}};
void empty(const SliceBinding& b){CHECK(!b.mapping.address&&!b.mapping.file.inode&&same_slice(b.slice,{}));}
void test(const std::string& name,const fs::path& fixture,const fs::path& root){
  fs::create_directories(root);std::string pattern=(root/"case-XXXXXX").string();CHECK(mkdtemp(pattern.data()));
  const auto path=fs::path(pattern)/"fixture.dylib";
  if(name=="universal"){
    std::ifstream in(fixture,std::ios::binary);slice_fixture::Bytes thin((std::istreambuf_iterator<char>(in)),{});CHECK(thin.size()>32);
    slice_fixture::Bytes fat(16384+thin.size());slice_fixture::be32(fat,0,0xcafebabe);slice_fixture::be32(fat,4,1);
    for(unsigned j=0;j<2;++j)for(unsigned i=0;i<4;++i)fat[8+j*4+i]=thin[4+j*4+3-i];
    slice_fixture::be32(fat,16,16384);slice_fixture::be32(fat,20,thin.size());slice_fixture::be32(fat,24,14);
    std::copy(thin.begin(),thin.end(),fat.begin()+16384);std::ofstream out(path,std::ios::binary);out.write(reinterpret_cast<const char*>(fat.data()),fat.size());CHECK(out.good());
  }else CHECK(fs::copy_file(fixture,path));
  void* handle=dlopen(path.c_str(),RTLD_NOW|RTLD_LOCAL);if(!handle)std::fprintf(stderr,"dlopen: %s\n",dlerror());CHECK(handle);
  void* symbol=dlsym(handle,"sh3_image_fixture");CHECK(symbol);Dl_info info{};CHECK(dladdr(symbol,&info));const auto address=reinterpret_cast<std::uintptr_t>(info.dli_fbase);
  MacOSSliceMappings maps;SliceBinding a{},b{};CHECK(maps.read(address,a)&&valid_slice_binding(a));
  if(name=="thin"||name=="universal"){
    CHECK(maps.read(address,b)&&same_slice(a.slice,b.slice)&&same_file(a.mapping.file,b.mapping.file));
    CHECK(a.slice.format==(name=="thin"?SliceFormat::thin:SliceFormat::fat32));CHECK(a.slice.offset==(name=="thin"?0:16384));
    if(name=="universal"){MacOSMappingSource strict;MappedFile rejected{};CHECK(!strict.read(address,rejected)&&!rejected.address);}
  }else if(name=="replace"||name=="unlink"){
    if(name=="replace"){auto replacement=fs::path(pattern)/"replacement";CHECK(fs::copy_file(fixture,replacement));fs::rename(replacement,path);}
    else fs::rename(path,fs::path(pattern)/"removed");
    CHECK(!maps.read(address,b));empty(b);CHECK(maps.failure()==SliceFailure::identity);
    CHECK(!maps.read(address,b));empty(b);
  }else if(name=="cow"){
    CHECK(mach_vm_protect(mach_task_self(),address,4096,false,VM_PROT_READ|VM_PROT_WRITE|VM_PROT_COPY)==KERN_SUCCESS);
    auto* flags=reinterpret_cast<volatile std::uint8_t*>(address+24);*flags^=1;
    CHECK(!maps.read(address,b)&&maps.failure()==SliceFailure::header);empty(b);
  }else if(name=="fork"){
    auto child=fork();CHECK(child>=0);if(!child)_exit(!maps.read(address,b)&&!b.mapping.address?0:1);
    int status{};CHECK(waitpid(child,&status,0)==child&&WIFEXITED(status)&&WEXITSTATUS(status)==0);CHECK(maps.read(address,b));
  }else if(name=="api"){
    for(int at:{1,2,3}){pid_calls=0;change_pid_at=at;forced=path.string();MacOSSliceMappings bad({pid,locate});CHECK(!bad.read(address,b));empty(b);CHECK(!bad.read(address,b));}
    change_pid_at=0;forced.clear();MacOSSliceMappings missing({pid,locate});CHECK(!missing.read(address,b));empty(b);
    forced=fixture.string();MacOSSliceMappings other({pid,locate});CHECK(!other.read(address,b)&&other.failure()==SliceFailure::identity);
    MacOSSliceMappings no_pid({nullptr,locate}),no_path({pid,nullptr});CHECK(!no_pid.read(address,b)&&!no_path.read(address,b));empty(b);
  }else if(name=="invalid"){
    for(auto bad_address:{std::uintptr_t(0),std::uintptr_t(1),address+1}){MacOSSliceMappings bad;CHECK(!bad.read(bad_address,b));empty(b);CHECK(!bad.read(address,b));}
  }else if(name=="origins"){
    Events events;MacOSSliceMappings slices;MacOSPlatformOrigins origins(events,slices);CHECK(origins.failure()==PlatformOriginFailure::none);
    ImageSnapshot snapshot{};CHECK(events.read(snapshot));std::array<ImageOrigin,image_capacity> first{};unsigned external=0,cache=0;
    for(unsigned pass=0;pass<2;++pass)for(std::size_t i=0;i<snapshot.count;++i){ImageOrigin o{};CHECK(origins.read(snapshot.addresses[i],o));
      if(o.kind==ImageOriginKind::application){CHECK(valid_slice_binding({o.application,o.slice}));if(!pass)++external;}
      else{CHECK(o.kind==ImageOriginKind::platform_cache&&same_slice(o.slice,{}));if(!pass)++cache;}
      if(pass)CHECK(same_slice(first[i].slice,o.slice)&&same_file(first[i].application.file,o.application.file));else first[i]=o;
    }
    CHECK(external>=2&&cache>0);
  }else CHECK(false);
  CHECK(dlclose(handle)==0);
}
}
int main(int argc,char** argv){CHECK(argc==4);test(argv[1],argv[2],argv[3]);}
