#include "sh3_observer/macos_region_vnode.hpp"
#include "sh3_observer/macos_image_identity.hpp"
#include "check.hpp"
#include <cerrno>
#include <cstring>
#include <filesystem>
#include <fcntl.h>
#include <string>
#include <sys/mman.h>
#include <sys/proc_info.h>
#include <sys/stat.h>
#include <sys/wait.h>
#include <unistd.h>
using namespace sh3::observer;
namespace {
bool empty(const RegionVnode& r) {
  return !r.address && !r.size && !r.region_offset && same_file(r.file,{});
}
struct Fixture {
  std::size_t page = static_cast<std::size_t>(sysconf(_SC_PAGESIZE));
  std::string path;
  int fd{-1}; void* base{MAP_FAILED};
  explicit Fixture(const std::string& directory) : path(directory+"/file") {
    CHECK(std::filesystem::create_directories(directory));
    fd = open(path.c_str(),O_RDWR|O_CREAT|O_EXCL,0600); CHECK(fd >= 0);
    CHECK(ftruncate(fd,static_cast<off_t>(3*page)) == 0);
    const char byte = 17; CHECK(pwrite(fd,&byte,1,static_cast<off_t>(page)) == 1);
    base = mmap(nullptr,page,PROT_READ|PROT_WRITE,MAP_PRIVATE,fd,static_cast<off_t>(page));
    CHECK(base != MAP_FAILED);
  }
  std::uint64_t address() { return reinterpret_cast<std::uint64_t>(base); }
  ~Fixture() { CHECK(munmap(base,page) == 0); CHECK(close(fd) == 0); }
};
void file(const std::string& directory, bool cow, bool replaced) {
  Fixture f(directory); MacOSRegionVnodeSource source; MacOSFileAnchor held(f.path);
  FileObject original{}; CHECK(held.read(original));
  RegionVnode before{},after{};
  CHECK(source.query(f.address()+13,before) == VnodeQuery::found);
  CHECK(before.address == f.address() && before.size == f.page && before.region_offset == f.page);
  CHECK(same_file(before.file,original));
  if (cow) {
    *static_cast<volatile char*>(f.base) = 39;
    char disk{}; CHECK(pread(f.fd,&disk,1,static_cast<off_t>(f.page)) == 1 && disk == 17);
    CHECK(*static_cast<volatile char*>(f.base) == 39);
  }
  if (replaced) {
    CHECK(rename(f.path.c_str(),(f.path+".old").c_str()) == 0);
    const auto fd = open(f.path.c_str(),O_RDWR|O_CREAT|O_EXCL,0600); CHECK(fd >= 0);
    CHECK(ftruncate(fd,static_cast<off_t>(3*f.page)) == 0); CHECK(close(fd) == 0);
    MacOSFileAnchor replacement(f.path); FileObject other{}; CHECK(replacement.read(other));
    CHECK(other.inode != original.inode);
    CHECK(source.query(f.address(),after) == VnodeQuery::found);
    CHECK(after.file.inode == original.inode && after.file.device == original.device);
    CHECK(!same_file(after.file,other));
    FileObject gone{}; CHECK(!held.read(gone));
  } else {
    CHECK(source.query(f.address(),after) == VnodeQuery::found);
    CHECK(same_file(before.file,after.file)); // COW retains vnode but changes resident bytes.
  }
}
void anonymous() {
  const auto page = static_cast<std::size_t>(sysconf(_SC_PAGESIZE));
  void* p = mmap(nullptr,page,PROT_READ|PROT_WRITE,MAP_ANON|MAP_PRIVATE,-1,0); CHECK(p != MAP_FAILED);
  *static_cast<volatile char*>(p) = 42;
  MacOSRegionVnodeSource source; RegionVnode r{}; r.size = 99;
  CHECK(source.query(reinterpret_cast<std::uint64_t>(p),r) == VnodeQuery::no_vnode && empty(r));
  CHECK(munmap(p,page) == 0);
}
void forked() {
  MacOSRegionVnodeSource source; const auto pid = fork(); CHECK(pid >= 0);
  if (pid == 0) { RegionVnode r{}; r.size = 99; CHECK(source.query(4096,r) == VnodeQuery::unavailable && empty(r)); _exit(0); }
  int status{}; pid_t waited;
  do { waited = waitpid(pid,&status,0); } while (waited < 0 && errno == EINTR);
  CHECK(waited == pid && WIFEXITED(status) && WEXITSTATUS(status) == 0);
}
struct Api {
  int pid{42}, calls{}, changed_at{}, info_calls{}, size_delta{};
  proc_regionwithpathinfo r{};
  Api() {
    r.prp_prinfo.pri_address = 4096; r.prp_prinfo.pri_size = 4096; r.prp_prinfo.pri_offset = 8192;
    auto& s = r.prp_vip.vip_vi.vi_stat;
    s.vst_mode = S_IFREG|0600; s.vst_dev = 5; s.vst_ino = 123; s.vst_size = 12288;
    s.vst_mtime = 11; s.vst_ctime = 12; s.vst_mtimensec = 13; s.vst_ctimensec = 14;
    std::strcpy(r.prp_vip.vip_path,"/untrusted/path");
  }
} api;
int pid() { ++api.calls; return api.changed_at && api.calls >= api.changed_at ? 43 : api.pid; }
int info(int owner, int flavor, std::uint64_t address, void* output, int size) {
  CHECK(owner == 42 && flavor == PROC_PIDREGIONPATHINFO && address != 0 && size == sizeof(api.r));
  ++api.info_calls; std::memcpy(output,&api.r,sizeof(api.r)); return size+api.size_delta;
}
void expect(VnodeQuery result, std::uint64_t address = 4113) {
  MacOSRegionVnodeSource source({pid,info}); RegionVnode r{}; r.size = 99;
  CHECK(source.query(address,r) == result);
  if (result == VnodeQuery::found) {
    const auto& s = api.r.prp_vip.vip_vi.vi_stat;
    CHECK(r.address == api.r.prp_prinfo.pri_address && r.size == api.r.prp_prinfo.pri_size && r.region_offset == api.r.prp_prinfo.pri_offset);
    CHECK(same_file(r.file,{s.vst_dev,s.vst_ino,static_cast<std::uint64_t>(s.vst_size),s.vst_mtime,s.vst_ctime,static_cast<std::uint32_t>(s.vst_mtimensec),static_cast<std::uint32_t>(s.vst_ctimensec)}));
  } else CHECK(empty(r));
}
void failures() {
  for (unsigned i = 0; i < 9; ++i) {
    api = {}; MacOSVnodeCalls calls{pid,info};
    if (i == 0) calls.pid = nullptr;
    if (i == 1) calls.info = nullptr;
    if (i == 2) api.pid = 0;
    if (i == 3) api.changed_at = 2;
    if (i == 4) api.changed_at = 3;
    if (i == 5) api.size_delta = -1;
    if (i == 6) api.size_delta = 1;
    if (i == 7) api.size_delta = -static_cast<int>(sizeof(api.r));
    MacOSRegionVnodeSource source(calls); RegionVnode r{}; r.size = 99;
    CHECK(source.query(i == 8 ? 0 : 4113,r) == VnodeQuery::unavailable && empty(r));
    CHECK(api.info_calls == (i >= 4 && i <= 7 ? 1 : 0));
  }
  api = {}; expect(VnodeQuery::found);
  api = {}; api.r.prp_prinfo.pri_flags = PROC_REGION_SUBMAP; expect(VnodeQuery::submap);
  api = {}; api.r.prp_vip = {}; expect(VnodeQuery::no_vnode);
  api = {}; std::memset(api.r.prp_vip.vip_path,'x',sizeof(api.r.prp_vip.vip_path)); expect(VnodeQuery::found);
}
void intervals() {
  for (const auto address : {4096ULL,4113ULL,8191ULL}) { api = {}; expect(VnodeQuery::found,address); }
  for (const auto address : {4095ULL,8192ULL,8193ULL}) { api = {}; expect(VnodeQuery::unavailable,address); }
  api = {}; api.r.prp_prinfo.pri_size = 0; expect(VnodeQuery::unavailable);
  api = {}; api.r.prp_prinfo.pri_address = UINT64_MAX-4095; expect(VnodeQuery::unavailable,UINT64_MAX-2);
  api = {}; api.r.prp_prinfo.pri_offset = UINT64_MAX-4095; expect(VnodeQuery::unavailable);
  api = {}; api.r.prp_prinfo.pri_address = UINT64_MAX-4096; expect(VnodeQuery::found,UINT64_MAX-1);
  api = {}; api.r.prp_prinfo.pri_offset = UINT64_MAX-4096; expect(VnodeQuery::found);
}
void malformed() {
  for (unsigned i = 0; i < 14; ++i) {
    api = {}; auto& s = api.r.prp_vip.vip_vi.vi_stat;
    if (i == 0) s.vst_mode = S_IFDIR|0700;
    if (i == 1) s.vst_size = 0;
    if (i == 2) s.vst_size = -1;
    if (i == 3) s.vst_mtimensec = -1;
    if (i == 4) s.vst_ctimensec = -1;
    if (i == 5) s.vst_mtimensec = 1000000000;
    if (i == 6) s.vst_ctimensec = 1000000000;
    if (i == 7) s.vst_dev = 0;
    if (i == 8) s.vst_ino = 0;
    if (i == 9) s.vst_mtime = -1;
    if (i == 10) s.vst_ctime = -1;
    if (i == 11) { s = {}; s.vst_mtime = 1; }
    if (i == 12) { s = {}; s.vst_ctime = 1; }
    if (i == 13) { s = {}; s.vst_mtimensec = 1; }
    expect(VnodeQuery::unavailable);
  }
}
}
int main(int argc, char** argv) {
  CHECK(argc == 3); const std::string name = argv[1];
  if (name == "file" || name == "cow" || name == "replaced") file(argv[2],name == "cow",name == "replaced");
  else if (name == "anonymous") anonymous(); else if (name == "fork") forked();
  else if (name == "api") failures(); else if (name == "intervals") intervals();
  else if (name == "malformed") malformed(); else CHECK(false);
}
