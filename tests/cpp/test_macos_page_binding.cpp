#include "sh3_observer/macos_page_binding.hpp"
#include "check.hpp"
#include <filesystem>
#include <fcntl.h>
#include <sys/mman.h>
#include <sys/wait.h>
#include <mach/vm_statistics.h>
#include <unistd.h>
#include <string>
using namespace sh3::observer;
namespace fs=std::filesystem;
namespace {
int api_mode{},pid_calls{},disposition=VM_PAGE_QUERY_PAGE_PRESENT|VM_PAGE_QUERY_PAGE_EXTERNAL;
int fake_pid(){++pid_calls;return api_mode==1?0:((api_mode==2&&pid_calls==2)||(api_mode==3&&pid_calls==3)?22:11);}
kern_return_t fake_copy(vm_map_read_t,mach_vm_address_t,mach_vm_size_t,mach_vm_address_t,mach_vm_size_t* count) {
  *count=api_mode==5?0:(api_mode==6?2:1);return api_mode==4?KERN_FAILURE:KERN_SUCCESS;
}
kern_return_t fake_info(vm_map_read_t,mach_vm_address_t,vm_page_info_flavor_t,vm_page_info_t raw,mach_msg_type_number_t* count) {
  auto* p=reinterpret_cast<vm_page_info_basic_data_t*>(raw);*p={};p->object_id=42;p->offset=7;p->disposition=disposition;
  *count=VM_PAGE_INFO_BASIC_COUNT+(api_mode==8?-1:(api_mode==9?1:0));return api_mode==7?KERN_FAILURE:KERN_SUCCESS;
}
void api_failures() {
  for(int mode=1;mode<=9;++mode){api_mode=mode;pid_calls=0;MacOSPageSource source({fake_pid,fake_copy,fake_info});PageReading out{99,88,true,true,true};CHECK(!source.read(0x1000,out));CHECK(out.object==0&&out.offset==0&&!out.resident&&!out.external&&!out.modified);}
  api_mode=0;
  for(int mode=0;mode<3;++mode){MacOSPageCalls calls{fake_pid,fake_copy,fake_info};if(mode==0)calls.pid=nullptr;if(mode==1)calls.copy=nullptr;if(mode==2)calls.info=nullptr;MacOSPageSource source(calls);PageReading out{};CHECK(!source.read(0x1000,out));}
  for(int flag:{0,VM_PAGE_QUERY_PAGE_DIRTY,VM_PAGE_QUERY_PAGE_COPIED,VM_PAGE_QUERY_PAGE_PAGED_OUT,VM_PAGE_QUERY_PAGE_FICTITIOUS,VM_PAGE_QUERY_PAGE_CS_TAINTED}) {
    disposition=VM_PAGE_QUERY_PAGE_PRESENT|VM_PAGE_QUERY_PAGE_EXTERNAL|flag;MacOSPageSource source({fake_pid,fake_copy,fake_info});PageReading out{};CHECK(source.read(0x1000,out));CHECK(out.object==42&&out.offset==7&&out.resident&&out.external);CHECK(out.modified==(flag!=0));
  }
}
constexpr std::size_t length=65536;
void create(const fs::path& path) {
  int fd=open(path.c_str(),O_CREAT|O_EXCL|O_RDWR,0600);CHECK(fd>=0);
  std::string data(length,'q');CHECK(write(fd,data.data(),data.size())==static_cast<ssize_t>(data.size()));CHECK(fsync(fd)==0);CHECK(close(fd)==0);
}
struct Mapping {
  void* data{};
  explicit Mapping(const fs::path& path) {
    int fd=open(path.c_str(),O_RDONLY);CHECK(fd>=0);data=mmap(nullptr,length,PROT_READ|PROT_WRITE,MAP_PRIVATE,fd,0);CHECK(data!=MAP_FAILED);CHECK(close(fd)==0);
  }
  ~Mapping(){CHECK(munmap(data,length)==0);}
  std::uintptr_t address(std::size_t offset=0) const {return reinterpret_cast<std::uintptr_t>(data)+offset;}
};
void test(const std::string& name,const fs::path& base) {
  fs::create_directories(base);auto pattern=(base/"case-XXXXXX").string();CHECK(mkdtemp(pattern.data()));fs::path dir=pattern;
  create(dir/"a");create(dir/"b");Mapping mapped(dir/"a");
  MacOSPageSource pages;MacOSPageAnchor anchor((dir/"a").string());
  PageBinding guard(mapped.address(name=="offset"?4219:0),anchor,pages);
  if(name=="paths") {
    fs::create_symlink("a",dir/"link");fs::create_directory_symlink(dir,dir.string()+"-link");
    for(const auto& path:{std::string{},std::string("a"),std::string("/"),dir.string()+"/",dir.string()+"//a",dir.string()+"/../a",dir.string()+"/./a",dir.string()+"/missing",dir.string()+"/link",dir.string()+"-link/a",dir.string(),std::string("/x\0y",4),std::string("/")+std::string(4097,'x'),dir.string()+"/"+std::string(256,'x')}) {
      MacOSPageAnchor bad(path);PageFileReading out{};CHECK(!bad.read(out));CHECK(out.file.inode==0);
    }
    int fd=open((dir/"empty").c_str(),O_CREAT|O_EXCL|O_RDWR,0600);CHECK(fd>=0);close(fd);
    MacOSPageAnchor empty((dir/"empty").string());PageFileReading out{};CHECK(!empty.read(out));return;
  }
  if(name=="inaccessible") {
    PageReading out{};CHECK(!pages.read(0,out));CHECK(!pages.read(1,out));CHECK(out.object==0);
    CHECK(mprotect(mapped.data,length,PROT_NONE)==0);CHECK(guard.sample().failure==PageFailure::unavailable);return;
  }
  if(name=="different_file") {
    MacOSPageAnchor copy((dir/"b").string());PageBinding wrong(mapped.address(),copy,pages);
    CHECK(wrong.sample().failure==PageFailure::mismatch);CHECK(wrong.sample().file.inode==0);return;
  }
  auto before=guard.sample();CHECK(before.failure==PageFailure::none);CHECK(before.file.inode!=0);CHECK(before.object!=0);
  if(name=="stable"||name=="offset") {
    CHECK(before.offset==(name=="offset"?4219U:0U));CHECK(guard.sample().failure==PageFailure::none);return;
  }
  if(name=="fork") {
    auto child=fork();CHECK(child>=0);
    if(child==0){PageReading page{};PageFileReading file{};_exit(!pages.read(mapped.address(),page)&&!anchor.read(file)&&guard.sample().failure==PageFailure::unavailable?0:1);}
    int status{};CHECK(waitpid(child,&status,0)==child);CHECK(WIFEXITED(status)&&WEXITSTATUS(status)==0);CHECK(guard.sample().failure==PageFailure::none);return;
  }
  PageFailure expected{};
  if(name=="cow") {
    static_cast<volatile char*>(mapped.data)[0]='z';expected=PageFailure::invalid;
  } else if(name=="replace") {
    fs::rename(dir/"b",dir/"a");expected=PageFailure::unavailable;
  } else if(name=="unlink") {
    fs::rename(dir/"a",dir/"removed");expected=PageFailure::unavailable;
  } else CHECK(false);
  auto failed=guard.sample();CHECK(failed.failure==expected);CHECK(failed.file.inode==0);CHECK(failed.object==0);CHECK(failed.offset==0);
  if(name=="cow")static_cast<volatile char*>(mapped.data)[0]='q';
  if(name=="unlink")fs::rename(dir/"removed",dir/"a");
  CHECK(guard.sample().failure==expected);
}
}
int main(int argc,char** argv){CHECK(argc==3);if(std::string(argv[1])=="api_failures")api_failures();else test(argv[1],argv[2]);}
