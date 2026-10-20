#include "sh3_observer/macos_image_identity.hpp"
#include "check.hpp"
#include <algorithm>
#include <atomic>
#include <cstring>
#include <dlfcn.h>
#include <filesystem>
#include <fstream>
#include <mach-o/dyld.h>
#include <sys/proc_info.h>
#include <sys/stat.h>
#include <sys/wait.h>
#include <thread>
#include <unistd.h>
using namespace sh3::observer;
namespace fs=std::filesystem;
namespace {
fs::path new_case(const fs::path& root) {
  fs::create_directories(root);
  std::string pattern=(root/"case-XXXXXX").string();
  CHECK(mkdtemp(pattern.data()));
  return pattern; // Preserve files; another test run uses another directory.
}
bool contains(const ImageSnapshot& s,std::uintptr_t a) {
  return std::find(s.addresses.begin(),s.addresses.begin()+s.count,a)!=s.addresses.begin()+s.count;
}
struct Library {
  void* handle{}; std::uintptr_t header{};
  explicit Library(const fs::path& path) {
    handle=dlopen(path.c_str(),RTLD_NOW|RTLD_LOCAL);
    if(!handle)std::fprintf(stderr,"dlopen: %s\n",dlerror());
    CHECK(handle);
    void* symbol=dlsym(handle,"sh3_image_fixture");CHECK(symbol);
    CHECK(reinterpret_cast<int(*)()>(symbol)()==11);
    Dl_info info{};CHECK(dladdr(symbol,&info)!=0);CHECK(info.dli_fbase);
    header=reinterpret_cast<std::uintptr_t>(info.dli_fbase);
  }
  void close(){CHECK(handle);CHECK(dlclose(handle)==0);handle=nullptr;}
  ~Library(){if(handle)close();}
};
void real_binding(const std::string& scenario,const fs::path& first,const fs::path& second,const fs::path& root) {
  const auto dir=new_case(root);
  const auto named=dir/"loaded.dylib";
  CHECK(fs::copy_file(first,named));
  Library lib(named);
  MacOSFileAnchor anchor(named.string());MacOSMappingSource map;
  ImageBinding binding(lib.header,anchor,map);
  auto before=binding.sample();CHECK(before.failure==ImageFailure::none);
  CHECK(before.mapping.address==lib.header);CHECK(before.mapping.file.inode!=0);
  if(scenario=="stable") {
    for(int i=0;i<100;++i)CHECK(binding.sample().failure==ImageFailure::none);
    return;
  }
  if(scenario=="unlink") {
    fs::rename(named,dir/"removed.dylib");
  } else {
    const auto replacement=dir/"replacement.dylib";
    CHECK(fs::copy_file(scenario=="replace_same" ? first : second,replacement));
    if(scenario=="replace_same")CHECK(fs::file_size(replacement)==fs::file_size(named));
    fs::rename(replacement,named);
    MacOSFileAnchor fresh(named.string());FileObject now{};CHECK(fresh.read(now));
    CHECK(now.inode!=before.mapping.file.inode);
    // The old mapping remains, even though the path resolves to another object.
    MappedFile loaded{};CHECK(map.read(lib.header,loaded));
    CHECK(loaded.file.inode==before.mapping.file.inode);CHECK(loaded.file.inode!=now.inode);
    ImageBinding mismatch(lib.header,fresh,map);CHECK(mismatch.sample().failure==ImageFailure::changed);
  }
  CHECK(binding.sample().failure==ImageFailure::unavailable);
  // Restore bytes at the path; the original instance must remain discarded.
  const auto restore=dir/"restore.dylib";CHECK(fs::copy_file(first,restore));fs::rename(restore,named);
  CHECK(binding.sample().failure==ImageFailure::unavailable);
  FileObject cleared{1,2,3,4,5,6,7};CHECK(!anchor.read(cleared));CHECK(cleared.inode==0);
}
void anchors(const fs::path& first,const fs::path& root) {
  const auto dir=new_case(root);FileObject out{};
  for(const auto& path: {std::string{},std::string("relative"),dir.string(),(dir/"missing").string(),std::string("/x\0y",4)}) {
    MacOSFileAnchor bad(path);CHECK(!bad.read(out));CHECK(out.inode==0);
  }
  fs::create_symlink(first,dir/"link");MacOSFileAnchor link((dir/"link").string());CHECK(!link.read(out));
  {std::ofstream empty(dir/"empty");}MacOSFileAnchor empty((dir/"empty").string());CHECK(!empty.read(out));
  const auto data=dir/"data";{std::ofstream file(data);file<<"1234";}
  MacOSFileAnchor changed(data.string());CHECK(changed.read(out));
  {std::ofstream file(data,std::ios::app);file<<"5";}
  CHECK(!changed.read(out));CHECK(out.inode==0);
}
void events(const fs::path& first) {
  ImageSnapshot a{},b{},c{},d{};CHECK(MacOSImageEvents::read(a));CHECK(a.count>0);
  Library lib(first);CHECK(MacOSImageEvents::read(b));CHECK(b.count==a.count+1);
  CHECK(b.revision==a.revision+1);CHECK(contains(b,lib.header));
  lib.close();CHECK(MacOSImageEvents::read(c));CHECK(c.count==a.count);
  CHECK(c.addresses==a.addresses);CHECK(c.revision==b.revision+1);
  Library again(first);CHECK(MacOSImageEvents::read(d));
  CHECK(d.revision==c.revision+1);CHECK(d.count==b.count);CHECK(contains(d,again.header));
  again.close();CHECK(MacOSImageEvents::read(d));CHECK(d.addresses==a.addresses);
  CHECK(d.revision==a.revision+4);
}
void threaded(const fs::path& first) {
  ImageSnapshot a{};CHECK(MacOSImageEvents::read(a));std::atomic<bool> done{false};
  std::thread worker([&]{for(int i=0;i<40;++i){Library lib(first);}done.store(true);});
  std::uint64_t last=a.revision;std::size_t reads=0;
  do {ImageSnapshot s{};CHECK(MacOSImageEvents::read(s));CHECK(s.revision>=last);last=s.revision;++reads;std::this_thread::yield();}while(!done.load());
  worker.join();ImageSnapshot end{};CHECK(MacOSImageEvents::read(end));
  CHECK(end.addresses==a.addresses);CHECK(end.revision==a.revision+80);CHECK(reads>0);
}
int api_mode=0,pids=0;
int fake_pid(){++pids;return api_mode==1 ? 0 : (api_mode==2 && pids>1 ? 101 : 100);}
int fake_info(int pid,int flavor,std::uint64_t address,void* buffer,int size) {
  CHECK(pid==100);CHECK(flavor==PROC_PIDREGIONPATHINFO);CHECK(address==4096);
  CHECK(size==sizeof(proc_regionwithpathinfo));
  proc_regionwithpathinfo r{};r.prp_prinfo.pri_address=4096;r.prp_prinfo.pri_size=4096;
  auto& s=r.prp_vip.vip_vi.vi_stat;s.vst_mode=S_IFREG|0600;s.vst_dev=7;s.vst_ino=21;s.vst_size=8192;
  s.vst_mtime=40;s.vst_ctime=41;s.vst_mtimensec=22;s.vst_ctimensec=23;
  switch(api_mode) {
    case 3:return -1;case 4:return size-1;
    case 5:s.vst_mode=S_IFDIR;break;case 6:s.vst_size=0;break;
    case 7:s.vst_mtimensec=-1;break;case 8:s.vst_ctimensec=-1;break;
    case 9:s.vst_mtimensec=1000000000;break;case 10:s.vst_ctimensec=1000000000;break;
    case 11:s.vst_dev=0;break;case 12:s.vst_ino=0;break;
    case 13:r.prp_prinfo.pri_address=8192;break;case 14:r.prp_prinfo.pri_size=0;break;
    case 15:r.prp_prinfo.pri_offset=1;break;case 16:r.prp_prinfo.pri_size=UINT64_MAX;break;
    case 17:s.vst_mtime=-1;break;case 18:s.vst_ctime=-1;break;
  }
  std::memcpy(buffer,&r,sizeof(r));return size;
}
void api() {
  MacOSMappingSource m({fake_pid,fake_info});MappedFile out{};
  for(api_mode=0;api_mode<=18;++api_mode){pids=0;const bool ok=m.read(4096,out);CHECK(ok==(api_mode==0));CHECK(ok ? out.file.inode==21 : out.file.inode==0);}
  CHECK(!m.read(0,out));
  MacOSMappingSource no_pid({nullptr,fake_info});CHECK(!no_pid.read(4096,out));
  MacOSMappingSource no_info({fake_pid,nullptr});CHECK(!no_info.read(4096,out));
  MacOSMappingSource real;CHECK(!real.read(1,out));CHECK(out.address==0);
}
void forked() {
  ImageSnapshot before{};CHECK(MacOSImageEvents::read(before));const pid_t child=fork();CHECK(child>=0);
  if(child==0){ImageSnapshot s{};_exit(!MacOSImageEvents::read(s)&&s.revision==0 ? 0 : 1);}
  int status{};CHECK(waitpid(child,&status,0)==child);CHECK(WIFEXITED(status));CHECK(WEXITSTATUS(status)==0);
  ImageSnapshot after{};CHECK(MacOSImageEvents::read(after));CHECK(after.revision==before.revision);
}
void cache_rejected() {
  // This is a classification witness only, never cache identity evidence.
  void* symbol=dlsym(RTLD_DEFAULT,"_dyld_get_image_header");CHECK(symbol);Dl_info info{};CHECK(dladdr(symbol,&info));
  CHECK(info.dli_fname);CHECK(_dyld_shared_cache_contains_path(info.dli_fname));
  MacOSMappingSource map;MappedFile out{};
  CHECK(!map.read(reinterpret_cast<std::uintptr_t>(info.dli_fbase),out));CHECK(out.file.inode==0);
}
}
int main(int argc,char** argv) {
  CHECK(argc==5);const std::string scenario=argv[1];
  if(scenario=="stable"||scenario=="replace_same"||scenario=="replace_different"||scenario=="unlink")real_binding(scenario,argv[2],argv[3],argv[4]);
  else if(scenario=="anchors")anchors(argv[2],argv[4]);
  else if(scenario=="events")events(argv[2]);
  else if(scenario=="threaded")threaded(argv[2]);
  else if(scenario=="api")api();
  else if(scenario=="fork")forked();
  else if(scenario=="cache")cache_rejected();
  else if(scenario=="executable") {
    MacOSFileAnchor executable(fs::absolute(argv[0]).string());MacOSMappingSource map;
    ImageBinding binding(reinterpret_cast<std::uintptr_t>(_dyld_get_image_header(0)),executable,map);
    CHECK(binding.sample().failure==ImageFailure::none);
  }
  else CHECK(false);
}
