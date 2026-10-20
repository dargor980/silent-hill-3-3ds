// Own fixtures; exact server, kernel socket calls and dispatch are private includes.
#include "check.hpp"
#include "sh3_observer/cooperative_gate.hpp"
#include "sh3_observer/completion.hpp"
#include "sh3_observer/wire.hpp"
#include "sh3_observer/host_epoch.hpp"
#include <array>
#include <atomic>
#include <cerrno>
#include <chrono>
#include <cstdio>
#include <cstring>
#include <functional>
#include <memory>
#include <mutex>
#include <span>
#include <string>
#include <thread>
#include <vector>
#include <sys/socket.h>
#include <sys/un.h>
#include <unistd.h>
using u8=std::uint8_t;using u16=std::uint16_t;using u32=std::uint32_t;using u64=std::uint64_t;
using mem8_t=u8;using mem16_t=u16;using mem32_t=u32;using mem64_t=u64;
using Gate=sh3::observer::CooperativeGate;using namespace std::chrono_literals;
#include "PINE.h"
std::array<u8,256> memory{};
std::atomic_uint reads{0},writes{0},loads{0},saves{0},snapshots{0};
std::mutex queue_mutex;
std::vector<std::function<void()>> queue;
std::size_t queued(){std::lock_guard lock(queue_mutex);return queue.size();}
void pump(){for(;;){std::function<void()> fn;{std::lock_guard lock(queue_mutex);if(queue.empty())break;fn=std::move(queue.front());queue.erase(queue.begin());}fn();}}
template<class T>T vtlb_ramRead(u32 address){CHECK(address+sizeof(T)<=memory.size());T value{};std::memcpy(&value,memory.data()+address,sizeof(T));reads++;return value;}
template<class T>void vtlb_ramWrite(u32 address,T value){CHECK(address+sizeof(T)<=memory.size());std::memcpy(memory.data()+address,&value,sizeof(T));writes++;}
enum class VMState {Shutdown,Running,Paused};
struct Error {std::string GetDescription() const{return "own failure";}};
namespace VMManager {
bool HasValidVM(){return true;}VMState GetState(){return VMState::Paused;}
std::string GetTitle(bool){return "own title";}std::string GetDiscSerial(){return "OWN-00001";}
std::string GetDiscVersion(){return "0.00";}u32 GetDiscCRC(){return 0x1234;}
void SaveStateToSlot(u8,bool,std::function<void(const std::string&)>){saves++;}
bool LoadStateFromSlot(u8,bool,Error*){loads++;return true;}
}
void SaveState_ReportSaveErrorOSD(const std::string&,u8){}
void SaveState_ReportLoadErrorOSD(const std::string&,u8,bool){}
namespace BuildVersion {constexpr auto GitRev="own-build";}
namespace fmt {std::string format(const char*,u32 v){char text[9];std::snprintf(text,sizeof(text),"%08x",v);return text;}}
namespace Threading {void SetNameOfCurrentThread(const char*){}}
namespace StringUtil {void Strlcpy(char* dst,const std::string& src,std::size_t size){CHECK(src.size()<size);std::memcpy(dst,src.c_str(),src.size()+1);}}
constexpr int Color_Red=1;
struct ConsoleDouble {template<class... T>void WriteLn(T&&...){}template<class... T>void Error(T&&...){}} Console;
namespace Host {void RunOnCPUThread(std::function<void()> fn,bool=false){std::lock_guard lock(queue_mutex);queue.push_back(std::move(fn));}}
namespace sh3::observer {
class EmulatorReader final:public Reader {
public:Snapshot snapshot(const Request&)noexcept override{snapshots++;return {};}
bool read_ram(u32,u32,u8*)noexcept override{CHECK(false);return false;}
};
#include "dispatch.inc"
}
#include "pine_server.inc"
void append(std::vector<u8>& v,u64 value,unsigned size){for(unsigned i=0;i<size;i++)v.push_back(static_cast<u8>(value>>(8*i)));}
std::vector<u8> frame(std::vector<u8> body){std::vector<u8> out;append(out,body.size()+4,4);out.insert(out.end(),body.begin(),body.end());return out;}
void send_bytes(int fd,const u8* p,std::size_t count){while(count){auto n=send(fd,p,count,0);CHECK(n>0);p+=n;count-=n;}}
void receive(int fd,u8* p,std::size_t count){while(count){auto n=recv(fd,p,count,0);CHECK(n>0);p+=n;count-=n;}}
std::vector<u8> response(int fd){std::vector<u8> out(4);receive(fd,out.data(),4);u32 size{};std::memcpy(&size,out.data(),4);CHECK(size>=5 && size<500000);out.resize(size);receive(fd,out.data()+4,size-4);return out;}
std::vector<u8> request(int fd,std::vector<u8> body){auto bytes=frame(std::move(body));send_bytes(fd,bytes.data(),bytes.size());return response(fd);}
int connect_client(){int fd=socket(AF_UNIX,SOCK_STREAM,0);CHECK(fd>=0);int no_signal=1;CHECK(setsockopt(fd,SOL_SOCKET,SO_NOSIGPIPE,&no_signal,sizeof(no_signal))==0);timeval timeout{5,0};CHECK(setsockopt(fd,SOL_SOCKET,SO_RCVTIMEO,&timeout,sizeof(timeout))==0);sockaddr_un addr{};addr.sun_family=AF_UNIX;std::string path=std::string(std::getenv("TMPDIR"))+"/pcsx2.sock.38187";CHECK(path.size()<sizeof(addr.sun_path));std::memcpy(addr.sun_path,path.c_str(),path.size()+1);CHECK(connect(fd,reinterpret_cast<sockaddr*>(&addr),sizeof(addr))==0);return fd;}
std::vector<u8> observer(){std::vector<u8> v{0xe0,1,0,0};v.resize(20);v[4]=1;for(u32 x:{1,0x100000,0x1000,4,0})append(v,x,4);return v;}
int main(int argc,char** argv){
 CHECK(argc==2);const std::string scenario=argv[1];CHECK(PINEServer::Initialize(38187));const auto generation=PINEServer::GetObserverGeneration();CHECK(generation>0);
 if(scenario=="idle_stop"){PINEServer::Deinitialize();CHECK(!PINEServer::IsInitialized());std::printf("{\"result\":\"PASS\",\"case\":\"%s\"}\n",argv[1]);return 0;}
 int fd=connect_client();CHECK(request(fd,{15})[4]==0);
 if(scenario=="status"){}
 else if(scenario=="memory"){
  std::vector<u8> write{6};append(write,16,4);append(write,0x12345678,4);CHECK(request(fd,write)[4]==0 && writes==1);
  std::vector<u8> read{2};append(read,16,4);auto reply=request(fd,read);u32 value{};std::memcpy(&value,reply.data()+5,4);CHECK(reply.size()==9 && value==0x12345678 && reads==1);
 }else if(scenario=="partial"){
  auto bytes=frame({15});send_bytes(fd,bytes.data(),2);send_bytes(fd,bytes.data()+2,2);send_bytes(fd,bytes.data()+4,1);CHECK(response(fd)[4]==0);
 }else if(scenario=="coalesced"){
  auto bytes=frame({15});auto second=bytes;bytes.insert(bytes.end(),second.begin(),second.end());send_bytes(fd,bytes.data(),bytes.size());CHECK(response(fd)[4]==0);CHECK(response(fd)[4]==0);
 }else if(scenario=="restart"){
  for(unsigned i=0;i<12;i++){PINEServer::Deinitialize();close(fd);CHECK(PINEServer::Initialize(38187));CHECK(PINEServer::GetObserverGeneration()!=generation);fd=connect_client();CHECK(request(fd,{15})[4]==0);}
 }else if(scenario=="stress_stop"){
  for(unsigned i=0;i<32;i++){
   PINEServer::Deinitialize();if(fd>=0)close(fd);CHECK(PINEServer::Initialize(38187));
   if(i%3==0)fd=-1;
   else {fd=connect_client();CHECK(request(fd,{15})[4]==0);if(i%3==2){auto bytes=frame({15});send_bytes(fd,bytes.data(),2);}}
  }
  if(fd<0)PINEServer::Deinitialize();
 }else if(scenario=="disconnect"){
  for(unsigned i=0;i<12;i++){shutdown(fd,SHUT_RDWR);close(fd);fd=connect_client();CHECK(request(fd,{15})[4]==0);}
 }else if(scenario=="closed"){
  auto closure=PINEServer::BeginObserverExclusion(Gate::Clock::now()+2s);CHECK(closure.poll()==Gate::State::held);std::vector<u8> write{4};append(write,16,4);write.push_back(71);CHECK(request(fd,write)[4]==255 && writes==0);closure.cancel();CHECK(request(fd,{15})[4]==0);
 }else if(scenario=="queued"){
  CHECK(request(fd,{10,3})[4]==0 && queued()==1);auto closure=PINEServer::BeginObserverExclusion(Gate::Clock::now()+2s);CHECK(closure.poll()==Gate::State::draining);CHECK(request(fd,{15})[4]==255);pump();CHECK(loads==1 && closure.poll()==Gate::State::held);closure.cancel();
 }else if(scenario=="discard"){
  CHECK(request(fd,{10,3})[4]==0 && queued()==1);auto closure=PINEServer::BeginObserverExclusion(Gate::Clock::now()+2s);CHECK(closure.poll()==Gate::State::draining);{std::lock_guard lock(queue_mutex);queue.clear();}CHECK(loads==0 && closure.poll()==Gate::State::held);closure.cancel();
 }else if(scenario=="observer_timeout"){
  auto reply=request(fd,observer());CHECK(reply[4]==0 && reply[10]==static_cast<u8>(sh3::observer::Status::timeout) && queued()==1);auto closure=PINEServer::BeginObserverExclusion(Gate::Clock::now()+2s);CHECK(closure.poll()==Gate::State::draining);pump();CHECK(snapshots==0 && closure.poll()==Gate::State::held);closure.cancel();
 }else if(scenario=="connected_stop" || scenario=="partial_stop"){
  if(scenario=="partial_stop"){auto bytes=frame({15});send_bytes(fd,bytes.data(),2);}
  PINEServer::Deinitialize();CHECK(!PINEServer::IsInitialized() && PINEServer::GetObserverGeneration()!=generation);close(fd);fd=-1;
 }else CHECK(false);
 if(fd>=0){shutdown(fd,SHUT_RDWR);close(fd);PINEServer::Deinitialize();}
 CHECK(!PINEServer::IsInitialized() && PINEServer::GetObserverGeneration()!=generation && queued()==0);
 std::printf("{\"result\":\"PASS\",\"case\":\"%s\"}\n",argv[1]);
}
