#include "check.hpp"
#include "sh3_observer/macos_process_birth.hpp"
#include <cerrno>
#include <cstring>
#include <libproc.h>
#include <spawn.h>
#include <string>
#include <sys/proc_info.h>
#include <sys/wait.h>
#include <unistd.h>
extern char** environ;
using namespace sh3::observer;
namespace {
void transfer(int fd, void* bytes, std::size_t size, bool sending) {
  auto* at = static_cast<unsigned char*>(bytes);
  while (size != 0) {
    const auto n = sending ? write(fd,at,size) : read(fd,at,size);
    if (n < 0 && errno == EINTR) continue;
    CHECK(n > 0); at += n; size -= static_cast<std::size_t>(n);
  }
}
void put(std::array<unsigned char,32>& wire, unsigned offset, std::uint64_t value) {
  for (unsigned i=0;i<8;++i) wire[offset+i] = static_cast<unsigned char>(value>>(8*i));
}
std::uint64_t get(const std::array<unsigned char,32>& wire,unsigned offset) {
  std::uint64_t value{};
  for (unsigned i=0;i<8;++i) value |= std::uint64_t{wire[offset+i]}<<(8*i);
  return value;
}
void wait_ok(pid_t child) {
  int status{}; pid_t result;
  do { result = waitpid(child,&status,0); } while (result < 0 && errno == EINTR);
  CHECK(result == child && WIFEXITED(status) && WEXITSTATUS(status) == 0);
}
void stable() {
  MacOSBirthSource b; MacOSNonceSource n; ProcessBirth identity(b,n);
  const auto first = identity.sample();
  CHECK(first.failure == BirthFailure::none && first.key.pid == static_cast<unsigned>(getpid()));
  CHECK(first.key.birth_ns > 0 && first.key.birth_ns % 1000 == 0);
  for (unsigned i=0;i<100;++i) {
    const auto next = identity.sample();
    CHECK(next.failure == BirthFailure::none && same_process_key(first.key,next.key));
  }
  identity.lose(); const auto lost = identity.sample();
  CHECK(lost.failure == BirthFailure::lost && same_process_key(lost.key,{}));
}
void child_mode() {
  MacOSBirthSource b; MacOSNonceSource n; ProcessBirth identity(b,n);
  const auto first = identity.sample(), next = identity.sample();
  CHECK(first.failure == BirthFailure::none && next.failure == BirthFailure::none);
  CHECK(same_process_key(first.key,next.key));
  std::array<unsigned char,32> wire{};
  put(wire,0,first.key.pid); put(wire,8,first.key.birth_ns);
  for (unsigned i=0;i<16;++i) wire[i+16] = first.key.nonce[i];
  transfer(STDOUT_FILENO,wire.data(),wire.size(),true);
  unsigned char acknowledge{}; transfer(STDIN_FILENO,&acknowledge,1,false);
  CHECK(acknowledge == 1);
}
ProcessKey spawn_key(const char* self) {
  int incoming[2], outgoing[2]; CHECK(pipe(incoming)==0 && pipe(outgoing)==0);
  for (const auto fd : {incoming[0],incoming[1],outgoing[0],outgoing[1]}) CHECK(fd>2);
  posix_spawn_file_actions_t actions; CHECK(posix_spawn_file_actions_init(&actions)==0);
  CHECK(posix_spawn_file_actions_adddup2(&actions,incoming[0],STDIN_FILENO)==0);
  CHECK(posix_spawn_file_actions_adddup2(&actions,outgoing[1],STDOUT_FILENO)==0);
  for (const auto fd : {incoming[0],incoming[1],outgoing[0],outgoing[1]})
    CHECK(posix_spawn_file_actions_addclose(&actions,fd)==0);
  char mode[] = "child"; char* args[] = {const_cast<char*>(self),mode,nullptr};
  pid_t pid{}; CHECK(posix_spawn(&pid,self,&actions,nullptr,args,environ)==0);
  CHECK(posix_spawn_file_actions_destroy(&actions)==0);
  CHECK(close(incoming[0])==0 && close(outgoing[1])==0);
  std::array<unsigned char,32> wire{}; transfer(outgoing[0],wire.data(),wire.size(),false);
  CHECK(get(wire,0)==static_cast<unsigned>(pid));
  proc_bsdinfo info{};
  const auto size=static_cast<int>(sizeof(info));
  CHECK(proc_pidinfo(pid,PROC_PIDTBSDINFO,0,&info,size)==size);
  CHECK(info.pbi_pid==static_cast<unsigned>(pid) && info.pbi_start_tvusec<1000000);
  CHECK(get(wire,8)==info.pbi_start_tvsec*1000000000+info.pbi_start_tvusec*1000);
  ProcessKey key{static_cast<unsigned>(pid),get(wire,8),{}};
  for (unsigned i=0;i<16;++i) key.nonce[i]=wire[i+16];
  CHECK(key.nonce != ProcessNonce{});
  unsigned char acknowledge=1; transfer(incoming[1],&acknowledge,1,true);
  CHECK(close(incoming[1])==0 && close(outgoing[0])==0); wait_ok(pid);
  return key;
}
void exec_restart(const char* self) {
  const auto first=spawn_key(self), second=spawn_key(self);
  CHECK(!same_process_key(first,second) && first.nonce!=second.nonce);
  // We observed two births; PID reuse is separately simulated by core tests.
}
void fork_inherited() {
  MacOSBirthSource b; MacOSNonceSource n; ProcessBirth identity(b,n);
  const auto original=identity.sample(); CHECK(original.failure==BirthFailure::none);
  const auto pid=fork(); CHECK(pid>=0);
  if(pid==0) {
    const auto rejected=identity.sample();
    CHECK(rejected.failure==BirthFailure::changed && same_process_key(rejected.key,{}));
    ProcessBirth fresh(b,n); const auto replacement=fresh.sample();
    CHECK(replacement.failure==BirthFailure::none && replacement.key.pid==static_cast<unsigned>(getpid()));
    CHECK(replacement.key.nonce!=original.key.nonce);
    _exit(0);
  }
  wait_ok(pid); CHECK(same_process_key(original.key,identity.sample().key));
}
struct ApiState {
  int pid{42}, next_pid{42}, count{}, size{static_cast<int>(sizeof(proc_bsdinfo))};
  std::uint32_t returned_pid{42}; std::uint64_t seconds{100}, micros{123456};
} api;
int fake_pid() { return ++api.count==1 ? api.pid : api.next_pid; }
int fake_info(int pid,int flavor,std::uint64_t arg,void* buffer,int size) {
  CHECK(pid==api.pid && flavor==PROC_PIDTBSDINFO && arg==0 && size==static_cast<int>(sizeof(proc_bsdinfo)));
  proc_bsdinfo info{}; info.pbi_pid=api.returned_pid;
  info.pbi_start_tvsec=api.seconds; info.pbi_start_tvusec=api.micros;
  std::memcpy(buffer,&info,sizeof(info)); return api.size;
}
int failed_entropy(void* buffer,std::size_t size) {
  CHECK(size==16); std::memset(buffer,0x7f,size); return -1;
}
int good_entropy(void* buffer,std::size_t size) {
  CHECK(size==16); std::memset(buffer,0x7f,size); return 0;
}
void api_failures() {
  for (unsigned variant=0;variant<9;++variant) {
    api={}; MacOSBirthCalls calls{fake_pid,fake_info};
    switch(variant) {
      case 0: calls.pid=nullptr; break; case 1: calls.info=nullptr; break;
      case 2: api.pid=0; break; case 3: api.size=-1; break;
      case 4: --api.size; break; case 5: api.returned_pid=43; break;
      case 6: api.next_pid=43; break; case 7: api.seconds=0; break;
      case 8: api.micros=1000000; break;
    }
    MacOSBirthSource source(calls); BirthReading out{99,99,99}; CHECK(!source.read(out));
    CHECK(out.pid==0 && out.seconds==0 && out.microseconds==0);
  }
  api={}; MacOSBirthSource source({fake_pid,fake_info}); BirthReading out{};
  CHECK(source.read(out) && out.pid==42 && out.seconds==100 && out.microseconds==123456);
  for (const auto fill : {static_cast<MacOSNonceSource::Fill>(nullptr),failed_entropy}) {
    ProcessNonce nonce{{1}}; MacOSNonceSource source(fill);
    CHECK(!source.fill(nonce) && nonce==ProcessNonce{});
  }
  ProcessNonce nonce{}; MacOSNonceSource entropy(good_entropy);
  CHECK(entropy.fill(nonce) && nonce.front()==0x7f && nonce.back()==0x7f);
}
}
int main(int argc,char** argv) {
  CHECK(argc==2); const std::string name=argv[1];
  if(name=="stable")stable();
  else if(name=="exec_restart")exec_restart(argv[0]);
  else if(name=="fork_inherited")fork_inherited();
  else if(name=="api_failures")api_failures();
  else if(name=="child")child_mode();
  else CHECK(false);
}
