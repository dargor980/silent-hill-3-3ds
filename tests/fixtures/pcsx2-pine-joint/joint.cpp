#include "sh3_observer/external_waits.hpp"
namespace VMManager::Internal {sh3::observer::ExternalWaits::Wait ObserveExternalCpuWait(bool);}
#include "joint_support.hpp"
#include "external_scope.inc"
#include <QThread>
#include <QEvent>
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

class EmuThread : public QObject {
 Q_OBJECT
public:bool isOnEmuThread()const{return QThread::currentThread()==thread();}
public Q_SLOTS:void runOnCPUThread(const std::function<void()>&);
};
EmuThread* g_emu_thread{};
namespace Host {void RunOnCPUThread(std::function<void()>,bool=false);}
#include "cpu_slot.inc"
#include "cpu_dispatch.inc"
std::array<u8,256> memory{};
std::atomic_uint reads{0},writes{0},loads{0},saves{0},snapshots{0};
template<class T>T vtlb_ramRead(u32 address){CHECK(address+sizeof(T)<=memory.size());T value{};std::memcpy(&value,memory.data()+address,sizeof(T));reads++;return value;}
template<class T>void vtlb_ramWrite(u32 address,T value){CHECK(address+sizeof(T)<=memory.size());std::memcpy(memory.data()+address,&value,sizeof(T));writes++;}
struct Error {std::string GetDescription() const{return "own failure";}};
namespace VMManager {
bool HasValidVM(){return true;}
std::string GetTitle(bool){return "own title";}std::string GetDiscSerial(){return "OWN-00001";}
std::string GetDiscVersion(){return "0.00";}u32 GetDiscCRC(){return 0x1234;}
void SaveStateToSlot(u8,bool,std::function<void(const std::string&)>){CHECK(s_observer_cpu_thread && !s_observer_pine_drain.effects_started());saves++;}
bool LoadStateFromSlot(u8,bool,Error*){CHECK(s_observer_cpu_thread && !s_observer_pine_drain.effects_started());loads++;return true;}
}
void SaveState_ReportSaveErrorOSD(const std::string&,u8){}
void SaveState_ReportLoadErrorOSD(const std::string&,u8,bool){}
namespace BuildVersion {constexpr auto GitRev="own-build";}
namespace fmt {std::string format(const char*,u32 v){char text[9];std::snprintf(text,sizeof(text),"%08x",v);return text;}}
namespace StringUtil {void Strlcpy(char* dst,const std::string& src,std::size_t size){CHECK(src.size()<size);std::memcpy(dst,src.c_str(),src.size()+1);}}
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
sh3::observer::CooperativeGate::Work enter_pine(){return PINEServer::s_observer_pine_gate.enter();}
void exercise(const std::string& scenario){
 CHECK(PINEServer::Initialize(38187));int fd=connect_client();CHECK(request(fd,{15})[4]==0);
 start();QEventLoop loop;
 const bool queued=scenario=="prior" || scenario=="discard" || scenario=="stop_pending" || scenario=="deadline";
 if(queued)CHECK(request(fd,{10,3})[4]==0);
 if(scenario=="timeout"){
  auto reply=request(fd,observer());CHECK(reply[4]==0 && reply[10]==static_cast<u8>(sh3::observer::Status::timeout));
 }
 queue(1,scenario=="deadline"?50ms:2000ms);
 if(queued || scenario=="timeout"){
  CHECK(step()==State::draining && !s_observer_pine_drain.effects_started());
  CHECK(vu1Thread.GetObserverStatus({1,1})==Status::invalid && MTGS::GetObserverStatus({1,1})==Status::invalid);
  CHECK(request(fd,{15})[4]==255);
 }else wait_held();
 if(scenario=="discard")QCoreApplication::removePostedEvents(g_emu_thread,QEvent::MetaCall);
 if(scenario=="generation" || scenario=="stop_pending"){
  const auto old=PINEServer::GetObserverGeneration();PINEServer::Deinitialize();close(fd);
  CHECK(PINEServer::GetObserverGeneration()!=old && step()==State::invalidated);
  StopObserverPineDrain();CHECK(s_observer_pine_result.state==State::invalidated);
  if(scenario=="stop_pending"){
   auto closure=PINEServer::BeginObserverExclusion(Clock::now()+2s);CHECK(closure.poll()==Gate::State::draining);
   QCoreApplication::removePostedEvents(g_emu_thread,QEvent::MetaCall);CHECK(closure.poll()==Gate::State::held);closure.cancel();
  }else check_released();
  CHECK(PINEServer::Initialize(38187));fd=connect_client();CHECK(request(fd,{15})[4]==0);queue(2,2s);qt_pump(&loop);
 }else if(scenario=="deadline"){
  until([]{return step()==State::timed_out;});CHECK(!s_observer_pine_drain.effects_started());
  StopObserverPineDrain();CHECK(s_observer_pine_result.state==State::timed_out && loads==0);
  {auto activity=VMManager::Internal::EnterObserverCpuActivity();loop.processEvents();}CHECK(loads==1);
  queue(2,2s);qt_pump(&loop);
 }else if(scenario=="late"){
  std::vector<u8> write{4};append(write,16,4);write.push_back(71);CHECK(request(fd,write)[4]==255 && writes==0);
  qt_pump(&loop);CHECK(request(fd,write)[4]==0 && writes==1);
 }else qt_pump(&loop);
 CHECK(s_observer_pine_result.state==State::completed && !s_observer_pine_drain.active() && pine_gate.enter());
 CHECK(loads==((scenario=="prior" || scenario=="deadline")?1u:0u) && snapshots==0);
 close_all();PINEServer::Deinitialize();close(fd);
}
int main(int argc,char** argv){
 QCoreApplication app(argc,argv);CHECK(argc==2);const std::string scenario=argv[1];
 CHECK(scenario=="prior" || scenario=="discard" || scenario=="timeout" || scenario=="generation" || scenario=="stop_pending" || scenario=="deadline" || scenario=="late");
 qRegisterMetaType<std::function<void()>>();EmuThread receiver;g_emu_thread=&receiver;
 s_observer_cpu_thread=true;s_observer_cpu_boundary.set_online(true);exercise(scenario);
 std::printf("{\"result\":\"PASS\",\"case\":\"%s\"}\n",argv[1]);
}
#include "frontend.moc"
