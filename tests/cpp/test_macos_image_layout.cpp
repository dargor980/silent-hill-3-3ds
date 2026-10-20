#include "sh3_observer/macos_image_layout.hpp"
#include "sh3_observer/macos_image_identity.hpp"
#include "image_layout_fixture.hpp"
#include "check.hpp"
#include <mach-o/dyld.h>
#include <sys/mman.h>
#include <sys/wait.h>
#include <unistd.h>
#include <cstdio>
using namespace sh3::observer;
namespace {
int mode{},pids{};
int pid(){++pids;return mode==1?0:((mode==2&&pids==2)||(mode==3&&pids==3)?22:11);}
kern_return_t copy(vm_map_read_t,mach_vm_address_t,mach_vm_size_t size,mach_vm_address_t,mach_vm_size_t* got){*got=mode==5?size-1:(mode==6?size+1:size);return mode==4?KERN_FAILURE:KERN_SUCCESS;}
void test(const std::string& name){
  auto address=reinterpret_cast<std::uintptr_t>(_dyld_get_image_header(0));MacOSImageBytes source(address);ImageLayout layout{};
  if(name=="self"){
    CHECK(read_image_layout(source,layout)==LayoutFailure::none&&layout.count>=3&&layout.type==2);return;
  }
  if(name=="inventory"){
    ImageSnapshot before{},after{};CHECK(MacOSImageEvents::read(before)&&before.count>1);
    for(std::size_t i=0;i<before.count;++i){MacOSImageBytes bytes(before.addresses[i]);auto result=read_image_layout(bytes,layout);if(result!=LayoutFailure::none)std::fprintf(stderr,"bad image address=%llx failure=%d\n",static_cast<unsigned long long>(before.addresses[i]),static_cast<int>(result));CHECK(result==LayoutFailure::none);}
    CHECK(MacOSImageEvents::read(after));CHECK(before.count==after.count&&before.revision==after.revision&&before.addresses==after.addresses);return;
  }
  if(name=="fork"){
    auto child=fork();CHECK(child>=0);if(child==0)_exit(read_image_layout(source,layout)==LayoutFailure::unavailable?0:1);
    int status{};CHECK(waitpid(child,&status,0)==child);CHECK(WIFEXITED(status)&&WEXITSTATUS(status)==0);CHECK(read_image_layout(source,layout)==LayoutFailure::none);return;
  }
  if(name=="api"){
    unsigned char bytes[32]{};std::size_t got{};
    for(int n=1;n<=6;++n){mode=n;pids=0;MacOSImageBytes item(0x10000,{pid,copy});got=99;CHECK(!item.read_at(0,bytes,sizeof(bytes),got)&&got==0);}
    mode=0;pids=0;
    for(int n=0;n<9;++n){MacOSImageReadCalls calls{pid,copy};if(n==0)calls.pid=nullptr;if(n==1)calls.copy=nullptr;MacOSImageBytes item(n==2?0:(n==3?UINTPTR_MAX-10:0x10000),calls);got=99;
      CHECK(!item.read_at(n==4?UINT64_MAX:(n==5?layout_command_limit+32:0),n==6?nullptr:bytes,n==7?0:(n==8?digest_block_size+1:32),got)&&got==0);
    }
    MacOSImageBytes good(0x10000,{pid,copy});CHECK(good.read_at(0,bytes,sizeof(bytes),got)&&got==sizeof(bytes));return;
  }
  CHECK(name=="fixture"||name=="unreadable");auto bytes=layout_fixture::valid();auto size=static_cast<std::size_t>(sysconf(_SC_PAGESIZE));CHECK(bytes.size()<size);
  auto* mapping=mmap(nullptr,size,PROT_READ|PROT_WRITE,MAP_PRIVATE|MAP_ANON,-1,0);CHECK(mapping!=MAP_FAILED);std::memcpy(mapping,bytes.data(),bytes.size());
  MacOSImageBytes fixture(reinterpret_cast<std::uintptr_t>(mapping));CHECK(read_image_layout(fixture,layout)==LayoutFailure::none&&layout.count==3);
  if(name=="unreadable"){CHECK(mprotect(mapping,size,PROT_NONE)==0);CHECK(read_image_layout(fixture,layout)==LayoutFailure::unavailable&&layout.count==0);}
  CHECK(munmap(mapping,size)==0);
}
}
int main(int argc,char** argv){CHECK(argc==2);test(argv[1]);}
