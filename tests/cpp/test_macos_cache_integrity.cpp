#include "sh3_observer/cache_range.hpp"
#include "sh3_observer/macos_page_binding.hpp"
#include "sh3_observer/macos_artifact_manifest.hpp"
#include "check.hpp"
#include <filesystem>
#include <fcntl.h>
#include <sys/mman.h>
#include <sys/wait.h>
#include <unistd.h>
using namespace sh3::observer;
namespace fs=std::filesystem;
namespace {
constexpr std::size_t length=65536;
std::string target,replacement;
int mode{},calls{};
ssize_t reader(int fd,void* data,std::size_t n,off_t offset){
  ++calls;
  if(mode==1)return -1;if(mode==2)return static_cast<ssize_t>(n)+1;
  const auto got=pread(fd,data,n,offset);
  if(calls==1){
    if(mode==3)fs::rename(replacement,target);
    if(mode==4){int other=open(target.c_str(),O_RDWR);CHECK(other>=0);char x='x';CHECK(pwrite(other,&x,1,123)==1);CHECK(fsync(other)==0);close(other);}
  }
  return mode==5&&got>0?got-1:got;
}
void create(const fs::path& path){
  int fd=open(path.c_str(),O_CREAT|O_EXCL|O_RDWR,0600);CHECK(fd>=0);std::string bytes(length,'q');
  CHECK(write(fd,bytes.data(),bytes.size())==static_cast<ssize_t>(bytes.size()));CHECK(fsync(fd)==0);CHECK(close(fd)==0);
}
std::string hex(const Sha256& sha){constexpr char digits[]="0123456789abcdef";std::string s;for(auto b:sha){s+=digits[b>>4];s+=digits[b&15];}return s;}
void test(const std::string& name,const fs::path& directory){
  CHECK(fs::create_directories(directory));auto dir=fs::canonical(directory);create(dir/"a");create(dir/"b");target=(dir/"a").string();replacement=(dir/"b").string();
  MacOSPageAnchor anchor(target,reader);MacOSSha256 hash;AnchoredDigest digest(anchor,anchor,hash,ArtifactDomain::system_cache);FileDigest value{};
  if(name=="read_failures"){
    for(int m:{1,2,5}){mode=m;calls=0;MacOSPageAnchor a(target,reader);MacOSSha256 h;AnchoredDigest d(a,a,h,ArtifactDomain::system_cache);
      CHECK(d.sample(value)==ManifestFailure::unavailable);CHECK(value.object.inode==0&&value.sha256==Sha256{});int before=calls;mode=0;CHECK(d.sample(value)==ManifestFailure::unavailable&&before==calls);
    }return;
  }
  if(name=="during_replace"||name=="during_write"){
    mode=name=="during_replace"?3:4;CHECK(digest.sample(value)==ManifestFailure::unavailable);int before=calls;mode=0;
    CHECK(digest.sample(value)==ManifestFailure::unavailable&&before==calls);return;
  }
  if(name=="byte_arguments"){
    for(int n=0;n<6;++n){MacOSPageAnchor a(target,n==5?nullptr:reader);char data[1]{};std::size_t got=99;
      CHECK(!a.read_at(n==3?length+1:0,n==0?nullptr:data,n==1?0:(n==2?digest_block_size+1:1),got)||n==4);
      if(n==4){CHECK(got==1);CHECK(a.read_at(length,data,1,got)&&got==0);}
      else {CHECK(got==0);PageFileReading page{};FileObject file{};CHECK(!a.read(page)&&!a.read(file));}
    }return;
  }
  CHECK(digest.sample(value)==ManifestFailure::none);CHECK(hex(value.sha256)=="418c410ad17dc40fb50368fd499548644db7111b2de7e68ad52fb5adbc72940c");
  FileObject identity{};PageFileReading reference{};CHECK(anchor.read(identity)&&anchor.read(reference));
  CHECK(same_file(value.object,identity)&&same_file(identity,reference.file));
  CHECK(digest.sample(value)==ManifestFailure::none);
  if(name=="stable")return;
  if(name=="fork"){
    auto child=fork();CHECK(child>=0);
    if(child==0){char b{};std::size_t got=99;FileDigest out{};_exit(!anchor.read_at(0,&b,1,got)&&got==0&&digest.sample(out)==ManifestFailure::unavailable?0:1);}
    int status{};CHECK(waitpid(child,&status,0)==child);CHECK(WIFEXITED(status)&&WEXITSTATUS(status)==0);CHECK(digest.sample(value)==ManifestFailure::none);return;
  }
  if(name=="replace"){
    fs::rename(dir/"b",dir/"a");CHECK(digest.sample(value)==ManifestFailure::unavailable);CHECK(!anchor.read(reference));return;
  }
  int fd=open(target.c_str(),O_RDONLY);CHECK(fd>=0);auto* data=mmap(nullptr,length,PROT_READ|PROT_WRITE,MAP_PRIVATE,fd,0);CHECK(data!=MAP_FAILED);close(fd);
  const auto address=reinterpret_cast<std::uintptr_t>(data);const auto page=static_cast<std::uint64_t>(sysconf(_SC_PAGESIZE));MacOSPageSource pages;
  CacheRangeGuard guard(value,{{address+3,length-6,3}},page,anchor,pages);
  auto result=guard.sample();CHECK(result.failure==PageFailure::none&&result.bytes==length-6&&result.pages==length/page);
  if(name=="range")CHECK(guard.sample().failure==PageFailure::none);
  else if(name=="middle_cow"){
    static_cast<volatile char*>(data)[page]='x';CHECK(guard.sample().failure==PageFailure::invalid);
    static_cast<volatile char*>(data)[page]='q';CHECK(guard.sample().failure==PageFailure::invalid);
  }else if(name=="middle_hole"){
    CHECK(mprotect(static_cast<char*>(data)+page,page,PROT_NONE)==0);CHECK(guard.sample().failure==PageFailure::unavailable);
    CHECK(mprotect(static_cast<char*>(data)+page,page,PROT_READ)==0);CHECK(guard.sample().failure==PageFailure::unavailable);
  }else CHECK(false);
  CHECK(munmap(data,length)==0);
}
}
int main(int argc,char** argv){CHECK(argc==3);test(argv[1],argv[2]);}
