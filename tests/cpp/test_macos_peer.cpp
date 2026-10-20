#include "sh3_observer/macos_peer.hpp"
#include "check.hpp"
#include <algorithm>
#include <bsm/libbsm.h>
#include <cstring>
#include <fcntl.h>
#include <libproc.h>
#include <limits>
#include <string>
#include <sys/proc_info.h>
#include <sys/un.h>
#include <sys/wait.h>
#include <unistd.h>
using namespace sh3::observer;
namespace {
int option_count{},info_count{},path_count{},fail_option{},fail_info{},fail_path{},short_option{},mutate_info{};
int opt(int fd,int level,int key,void* data,socklen_t* size) {
  ++option_count; if (option_count==fail_option) return -1;
  const auto r=::getsockopt(fd,level,key,data,size);if(option_count==short_option)--*size;return r;
}
int info(int pid,int flavor,std::uint64_t arg,void* data,int size) {
  ++info_count;if(info_count==fail_info)return 0;
  const auto r=::proc_pidinfo(pid,flavor,arg,data,size);
  if(mutate_info && info_count==2) {
    auto& p=*static_cast<proc_bsdinfo*>(data);
    if(mutate_info==1)++p.pbi_start_tvsec;
    if(mutate_info==2)p.pbi_start_tvusec=1000000;
    if(mutate_info==3)p.pbi_start_tvsec=std::numeric_limits<std::uint64_t>::max();
    if(mutate_info==4)p.pbi_uid^=1;
    if(mutate_info==5)p.pbi_ruid^=1;
    if(mutate_info==6)p.pbi_pid^=1;
    if(mutate_info==7)p.pbi_start_tvsec=0;
  }
  return r;
}
int path(audit_token_t* t,void* p,std::uint32_t size) {++path_count;return path_count==fail_path?0:proc_pidpath_audittoken(t,p,size);}
void reset(){option_count=info_count=path_count=fail_option=fail_info=fail_path=short_option=mutate_info=0;}
void absent(int fd,MacOSPeerCalls calls=macos_peer_calls()) {
  MacOSPeerIdentity p;p.pid=42;p.token.fill(255);CHECK(!read_macos_peer(fd,p,calls));
  CHECK(p.pid==0 && p.birth_ns==0 && std::all_of(p.token.begin(),p.token.end(),[](auto b){return b==0;}));
}
void absent_release(int fd,MacOSPeerCalls calls=macos_peer_calls()) {
  MacOSPeerIdentity p;p.pid=42;p.token.fill(255);CHECK(!read_macos_released_peer(fd,p,calls));
  CHECK(p.pid==0 && p.birth_ns==0 && std::all_of(p.token.begin(),p.token.end(),[](auto b){return b==0;}));
}
std::uint64_t little(const std::uint8_t* b,unsigned n){std::uint64_t v{};for(unsigned i=0;i<n;++i)v|=std::uint64_t{b[i]}<<(i*8);return v;}
}
int main(int argc,char**argv) {
  CHECK(argc>=2);const std::string mode=argv[1];
  if(mode=="child") {CHECK(argc==3);const int fd=std::stoi(argv[2]);CHECK(::send(fd,"E",1,0)==1);char c{};CHECK(::recv(fd,&c,1,0)==1);::close(fd);return 0;}
  if(mode=="process"||mode=="exec") {
    char directory[]="/tmp/sh3peer-XXXXXX";CHECK(::mkdtemp(directory));
    const std::string endpoint=std::string(directory)+"/peer";int server=::socket(AF_UNIX,SOCK_STREAM,0);CHECK(server>=0);
    sockaddr_un address{};address.sun_family=AF_UNIX;std::strcpy(address.sun_path,endpoint.c_str());
    CHECK(::bind(server,reinterpret_cast<sockaddr*>(&address),sizeof(address))==0);CHECK(::listen(server,1)==0);
    const pid_t child=::fork();CHECK(child>=0);
    if(child==0) {
      ::close(server);const int fd=::socket(AF_UNIX,SOCK_STREAM,0);CHECK(fd>=0);
      CHECK(::connect(fd,reinterpret_cast<sockaddr*>(&address),sizeof(address))==0);CHECK(::send(fd,"R",1,0)==1);
      char c{};CHECK(::recv(fd,&c,1,0)==1);
      if(mode=="exec") {const auto number=std::to_string(fd);::execl(argv[0],argv[0],"child",number.c_str(),static_cast<char*>(nullptr));::_exit(91);}
      ::close(fd);::_exit(0);
    }
    int fd=::accept(server,nullptr,nullptr);CHECK(fd>=0);char c{};CHECK(::recv(fd,&c,1,0)==1 && c=='R');
    MacOSPeerIdentity first{},last{};CHECK(read_macos_peer(fd,first));CHECK(first.pid==static_cast<unsigned>(child));
    CHECK(first.birth_ns==read_macos_birth(child));CHECK(::send(fd,"x",1,0)==1);
    if(mode=="exec") {
      CHECK(::recv(fd,&c,1,0)==1 && c=='E');CHECK(read_macos_peer(fd,last));
      CHECK(first.pid==last.pid && first.birth_ns==last.birth_ns && first.token!=last.token && first.pid_version!=last.pid_version);
      audit_token_t old{};std::memcpy(&old,first.token.data(),32);char path_buffer[PROC_PIDPATHINFO_MAXSIZE]{};
      CHECK(proc_pidpath_audittoken(&old,path_buffer,sizeof(path_buffer))==0);CHECK(::send(fd,"q",1,0)==1);
    }
    int status{};CHECK(::waitpid(child,&status,0)==child && WIFEXITED(status) && WEXITSTATUS(status)==0);
    absent(fd);absent_release(fd);CHECK(read_macos_birth(child)==0);::close(fd);::close(server);CHECK(::unlink(endpoint.c_str())==0);CHECK(::rmdir(directory)==0);return 0;
  }
  int sockets[2]{};CHECK(::socketpair(AF_UNIX,SOCK_STREAM,0,sockets)==0);const int fd=sockets[0];
  if(mode=="release_stable") {
    MacOSPeerIdentity first{},last{};CHECK(read_macos_peer(fd,first));absent_release(fd);
    CHECK(::shutdown(sockets[1],SHUT_WR)==0);CHECK(read_macos_released_peer(fd,last));
    CHECK(first.pid==last.pid && first.euid==last.euid && first.ruid==last.ruid &&
      first.birth_ns==last.birth_ns && first.pid_version==last.pid_version && first.token==last.token);
    absent(fd);std::array<std::uint8_t,56> bytes{};bytes.fill(255);
    CHECK(!sh3_macos_peer_v1(fd,bytes.data(),bytes.size()));
    CHECK(std::all_of(bytes.begin(),bytes.end(),[](auto b){return b==0;}));
  } else if(mode=="release_invalid") {
    absent_release(-1);absent_release(fd);CHECK(::send(sockets[1],"x",1,0)==1);
    CHECK(::shutdown(sockets[1],SHUT_WR)==0);absent_release(fd);
    char c{};CHECK(::recv(fd,&c,1,0)==1 && c=='x');MacOSPeerIdentity identity;CHECK(read_macos_released_peer(fd,identity));
    int file=::open("/dev/null",O_RDONLY);CHECK(file>=0);absent_release(file);::close(file);
    for(int family:{AF_UNIX,AF_INET}) {int other=::socket(family,SOCK_DGRAM,0);CHECK(other>=0);absent_release(other);::close(other);}
    int empty=::socket(AF_UNIX,SOCK_STREAM,0);CHECK(empty>=0);absent_release(empty);::close(empty);
  } else if(mode=="release_api") {
    CHECK(::shutdown(sockets[1],SHUT_WR)==0);const MacOSPeerCalls calls{opt,info,path};MacOSPeerIdentity p;
    reset();CHECK(read_macos_released_peer(fd,p,calls));CHECK(option_count==6&&info_count==2&&path_count==2);
    for(int n=1;n<=6;++n){reset();fail_option=n;absent_release(fd,calls);reset();short_option=n;absent_release(fd,calls);}
    for(int n=1;n<=2;++n){reset();fail_info=n;absent_release(fd,calls);reset();fail_path=n;absent_release(fd,calls);}
    reset();auto missing=calls;missing.option=nullptr;absent_release(fd,missing);missing=calls;missing.info=nullptr;absent_release(fd,missing);missing=calls;missing.path=nullptr;absent_release(fd,missing);
  } else if(mode=="release_changes") {
    CHECK(::shutdown(sockets[1],SHUT_WR)==0);
    for(int n=1;n<=7;++n){reset();mutate_info=n;absent_release(fd,{opt,info,path});}
  } else if(mode=="stable") {
    MacOSPeerIdentity a{},b{};CHECK(read_macos_peer(fd,a));CHECK(read_macos_peer(fd,b));
    CHECK(a.pid==static_cast<unsigned>(getpid()) && a.euid==geteuid() && a.ruid==getuid() && a.birth_ns==read_macos_birth(getpid()));
    CHECK(a.token==b.token);CHECK(::send(sockets[1],"d",1,0)==1);CHECK(read_macos_peer(fd,b));char c{};CHECK(::recv(fd,&c,1,0)==1 && c=='d');
  } else if(mode=="bridge") {
    std::array<std::uint8_t,56> wire{};CHECK(sh3_macos_peer_v1(fd,wire.data(),wire.size())==1);
    MacOSPeerIdentity p;CHECK(read_macos_peer(fd,p));CHECK(little(wire.data(),4)==p.pid && little(wire.data()+4,4)==p.euid && little(wire.data()+8,4)==p.ruid && little(wire.data()+12,4)==p.pid_version && little(wire.data()+16,8)==p.birth_ns);
    CHECK(std::equal(p.token.begin(),p.token.end(),wire.begin()+24));CHECK(sh3_macos_birth_v1(getpid())==p.birth_ns);
    CHECK(!sh3_macos_peer_v1(fd,nullptr,56));CHECK(!sh3_macos_peer_v1(fd,wire.data(),55));
    wire.fill(255);CHECK(!sh3_macos_peer_v1(-1,wire.data(),56));CHECK(std::all_of(wire.begin(),wire.end(),[](auto b){return b==0;}));
    CHECK(!sh3_macos_birth_v1(0));
  } else if(mode=="invalid") {
    absent(-1);int file=::open("/dev/null",O_RDONLY);CHECK(file>=0);absent(file);::close(file);
    for(int family:{AF_UNIX,AF_INET}) {int other=::socket(family,SOCK_DGRAM,0);CHECK(other>=0);absent(other);::close(other);}
    int tcp=::socket(AF_INET,SOCK_STREAM,0);CHECK(tcp>=0);absent(tcp);::close(tcp);
    int empty=::socket(AF_UNIX,SOCK_STREAM,0);CHECK(empty>=0);absent(empty);::close(empty);
    CHECK(::shutdown(sockets[1],SHUT_WR)==0);absent(fd);
  } else if(mode=="api") {
    const MacOSPeerCalls calls{opt,info,path};MacOSPeerIdentity p;reset();CHECK(read_macos_peer(fd,p,calls));CHECK(option_count==6&&info_count==2&&path_count==2);
    for(int n=1;n<=6;++n){reset();fail_option=n;absent(fd,calls);reset();short_option=n;absent(fd,calls);}
    for(int n=1;n<=2;++n){reset();fail_info=n;absent(fd,calls);reset();fail_path=n;absent(fd,calls);}
    reset();auto missing=calls;missing.option=nullptr;absent(fd,missing);missing=calls;missing.info=nullptr;absent(fd,missing);missing=calls;missing.path=nullptr;absent(fd,missing);
  } else if(mode=="changes") {
    for(int n=1;n<=7;++n){reset();mutate_info=n;absent(fd,{opt,info,path});}
    reset();mutate_info=1;CHECK(!read_macos_birth(getpid(),{opt,info,path}));
  } else CHECK(false);
  ::close(sockets[0]);::close(sockets[1]);
}
