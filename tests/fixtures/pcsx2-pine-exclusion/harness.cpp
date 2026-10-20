// Own data/doubles. Exact parser, formatting, safety and dispatch fragments are private.
#include "check.hpp"
#include "sh3_observer/cooperative_gate.hpp"
#include "sh3_observer/completion.hpp"
#include "sh3_observer/wire.hpp"
#include <array>
#include <condition_variable>
#include <cstdio>
#include <cstring>
#include <functional>
#include <span>
#include <string>
#include <thread>
#include <vector>
using u8=std::uint8_t; using u16=std::uint16_t; using u32=std::uint32_t; using u64=std::uint64_t;
using mem8_t=u8; using mem16_t=u16; using mem32_t=u32; using mem64_t=u64;
using Gate=sh3::observer::CooperativeGate; using State=Gate::State;
auto later() { return Gate::Clock::now()+std::chrono::seconds(10); }
std::array<u8,256> memory{};
unsigned reads=0,writes=0,saves=0,loads=0,save_errors=0,load_errors=0,snapshots=0;
unsigned common_cases=0,exclusion_cases=0; u64 digest=14695981039346656037ULL;
bool valid_vm=true,load_ok=true,retain_error=false,immediate=false,background=false;
std::vector<std::function<void()>> queue;
std::vector<std::function<void(const std::string&)>> error_callbacks;
std::thread cpu_worker;
std::mutex control_mutex; std::condition_variable control_cv;
bool block_write=false,write_entered=false,release_write=false;
bool block_snapshot=false,snapshot_entered=false,release_snapshot=false;
template<class T>T vtlb_ramRead(u32 address) { CHECK(address+sizeof(T)<=memory.size()); T v{};std::memcpy(&v,memory.data()+address,sizeof(T));++reads;return v; }
template<class T>void vtlb_ramWrite(u32 address,T value) {
  CHECK(address+sizeof(T)<=memory.size());
  if(block_write) { std::unique_lock<std::mutex> lock(control_mutex);write_entered=true;control_cv.notify_one();control_cv.wait(lock,[]{return release_write;}); }
  std::memcpy(memory.data()+address,&value,sizeof(T));++writes;
}
enum class VMState { Shutdown,Running,Paused }; VMState state=VMState::Paused;
struct Error { std::string GetDescription()const { return "own failure"; } };
namespace VMManager {
bool HasValidVM(){return valid_vm;} VMState GetState(){return state;}
std::string GetTitle(bool){return "own title";} std::string GetDiscSerial(){return "OWN-00001";}
std::string GetDiscVersion(){return "0.00";} u32 GetDiscCRC(){return 0x1234;}
void SaveStateToSlot(u8,bool,std::function<void(const std::string&)> callback) {++saves;if(retain_error)error_callbacks.push_back(std::move(callback));else callback("own failure");}
bool LoadStateFromSlot(u8 slot,bool,Error*) {++loads;memory[0]=slot;return load_ok;}
}
void SaveState_ReportSaveErrorOSD(const std::string&,u8){++save_errors;}
void SaveState_ReportLoadErrorOSD(const std::string&,u8,bool){++load_errors;}
namespace BuildVersion { constexpr auto GitRev="own-build"; }
namespace fmt { std::string format(const char*,u32 v){char buf[9];std::snprintf(buf,sizeof(buf),"%08x",v);return buf;} }
namespace Host {
void RunOnCPUThread(std::function<void()> callback,bool=false) {
  if(background) cpu_worker=std::thread(std::move(callback));
  else if(immediate) callback(); else queue.push_back(std::move(callback));
}
}
namespace sh3::observer {
class EmulatorReader final:public Reader {
public:
  Snapshot snapshot(const Request&)noexcept override {
    ++snapshots;
    if(block_snapshot) {std::unique_lock<std::mutex> lock(control_mutex);snapshot_entered=true;control_cv.notify_one();control_cv.wait(lock,[]{return release_snapshot;});}
    return {}; // Controlled pause failure: no real VM or acquisition.
  }
  bool read_ram(u32,u32,u8*)noexcept override {CHECK(false);return false;}
};
#ifdef SH3_ENABLE_OBSERVER
#include "dispatch.inc"
#endif
}
namespace PINEServer {
#include "gate.inc"
constexpr u32 MAX_IPC_SIZE=650000,MAX_IPC_RETURN_SIZE=450000;
enum IPCCommand:unsigned char {MsgRead8=0,MsgRead16,MsgRead32,MsgRead64,MsgWrite8,MsgWrite16,MsgWrite32,MsgWrite64,MsgVersion,MsgSaveState,MsgLoadState,MsgTitle,MsgID,MsgUUID,MsgGameVersion,MsgStatus,MsgSH3Observer=0xe0};
enum EmuStatus:u32 {Running,Paused,Shutdown}; enum IPCResult:unsigned char{IPC_OK=0,IPC_FAIL=255};
struct IPCBuffer{int size;std::vector<u8>buffer;};
template<class T>void ToResultVector(std::vector<u8>& out,T value,int offset){std::memcpy(out.data()+offset,&value,sizeof(T));}
// Explicit alignment-safe double; the provider's unaligned cast helper is not exercised.
template<class T>T FromSpan(std::span<u8> data,int offset){T value{};std::memcpy(&value,data.data()+offset,sizeof(T));return value;}
#include "safety.inc"
std::vector<u8>& MakeOkIPC(std::vector<u8>&,u32);
std::vector<u8>& MakeFailIPC(std::vector<u8>&,u32);
IPCBuffer ParseCommand(std::span<u8>,std::vector<u8>&,u32);
#ifdef SH3_ENABLE_OBSERVER
Gate::Closure BeginObserverExclusion(Gate::Clock::time_point);
#endif
}
#include "make-ok.inc"
#include "make-fail.inc"
#include "parse.inc"
#include "exclusion.inc"
void append(std::vector<u8>& out,u64 value,unsigned bytes){for(unsigned i=0;i<bytes;++i)out.push_back(static_cast<u8>(value>>(8*i)));}
std::vector<u8> command(unsigned opcode,unsigned size=0,u64 value=0x1234567812345678ULL){
  std::vector<u8> result{static_cast<u8>(opcode)};
  if(opcode<8){append(result,16,4);if(opcode>=4)append(result,value,size);}
  if(opcode==9||opcode==10)result.push_back(3);
  return result;
}
PINEServer::IPCBuffer parse(std::vector<u8> input){std::vector<u8> out(450000,0);return PINEServer::ParseCommand(input,out,static_cast<u32>(input.size()));}
void pump(){while(!queue.empty()){auto callback=std::move(queue.front());queue.erase(queue.begin());callback();}}
void reset(){
  CHECK(!cpu_worker.joinable());queue.clear();error_callbacks.clear();memory.fill(0);
  reads=writes=saves=loads=save_errors=load_errors=snapshots=0;
  valid_vm=load_ok=true;retain_error=immediate=background=false;state=VMState::Paused;
  block_write=write_entered=release_write=block_snapshot=snapshot_entered=release_snapshot=false;
}
void record(const PINEServer::IPCBuffer& reply){
  auto add=[](u64 value){digest^=value;digest*=1099511628211ULL;};
  add(reply.size);for(int i=0;i<reply.size;++i)add(reply.buffer[i]);for(auto b:memory)add(b);
  for(auto count:{reads,writes,saves,loads,save_errors,load_errors})add(count);
  ++common_cases;
}
template<class F>void extra(F f){reset();f();++exclusion_cases;}
int main(){
  for(unsigned i=0;i<4;++i){
    reset();auto reply=parse(command(4+i,1U<<i));CHECK(reply.buffer[4]==0&&writes==1);record(reply);
    auto read=parse(command(i));CHECK(read.buffer[4]==0&&reads==1);record(read);
  }
  for(unsigned opcode=0;opcode<8;++opcode){reset();auto input=command(opcode,1U<<(opcode%4));input.pop_back();auto reply=parse(input);CHECK(reply.buffer[4]==255&&reads==0&&writes==0);record(reply);}
  for(unsigned opcode=0;opcode<=15;++opcode){reset();valid_vm=false;auto reply=parse(command(opcode,1U<<(opcode%4)));CHECK(reply.buffer[4]==((opcode==8||opcode==15)?0:255));CHECK(reads==0&&writes==0);record(reply);}
  for(unsigned opcode=8;opcode<=15;++opcode){reset();auto reply=parse(command(opcode));CHECK(reply.buffer[4]==0);pump();record(reply);}
  reset();auto invalid=parse({255});CHECK(invalid.buffer[4]==255);record(invalid);
  reset();auto input=command(4,1);input.push_back(255);auto partial=parse(input);CHECK(partial.buffer[4]==255&&writes==1);record(partial);
  reset();load_ok=false;auto failed=parse(command(10));pump();CHECK(load_errors==1&&loads==1);record(failed);
  reset();retain_error=true;auto saved=parse(command(9));pump();CHECK(error_callbacks.size()==1);error_callbacks.front()("own failure");error_callbacks.clear();CHECK(save_errors==1);record(saved);
#ifdef SH3_ENABLE_OBSERVER
  extra([]{auto close=PINEServer::BeginObserverExclusion(later());CHECK(close.poll()==State::held);auto reply=parse(command(4,1));CHECK(reply.buffer[4]==255&&writes==0);close.cancel();CHECK(parse(command(4,1)).buffer[4]==0);});
  extra([]{auto reply=parse({255});CHECK(reply.buffer[4]==255);auto close=PINEServer::BeginObserverExclusion(later());CHECK(close.poll()==State::held);});
  extra([]{auto bytes=command(4,1);bytes.push_back(255);CHECK(parse(bytes).buffer[4]==255&&writes==1);auto close=PINEServer::BeginObserverExclusion(later());CHECK(close.poll()==State::held);});
  extra([]{CHECK(parse(command(10)).buffer[4]==0);auto close=PINEServer::BeginObserverExclusion(later());CHECK(close.poll()==State::draining);CHECK(parse(command(4,1)).buffer[4]==255);pump();CHECK(loads==1&&close.poll()==State::held);});
  extra([]{load_ok=false;CHECK(parse(command(10)).buffer[4]==0);auto close=PINEServer::BeginObserverExclusion(later());pump();CHECK(load_errors==1&&close.poll()==State::held);});
  extra([]{retain_error=true;CHECK(parse(command(9)).buffer[4]==0);auto close=PINEServer::BeginObserverExclusion(later());pump();CHECK(close.poll()==State::draining);error_callbacks.front()("own failure");CHECK(close.poll()==State::draining);error_callbacks.clear();CHECK(close.poll()==State::held);});
  extra([]{auto bytes=command(9);auto load=command(10);bytes.insert(bytes.end(),load.begin(),load.end());CHECK(parse(bytes).buffer[4]==0&&queue.size()==2);auto close=PINEServer::BeginObserverExclusion(later());auto copy=queue.front();queue.clear();CHECK(close.poll()==State::draining);copy={};CHECK(close.poll()==State::held&&loads==0&&saves==0);});
  extra([]{CHECK(parse(command(10)).buffer[4]==0);auto close=PINEServer::BeginObserverExclusion(Gate::Clock::now());CHECK(close.poll()==State::timed_out);queue.clear();CHECK(close.poll()==State::timed_out);CHECK(parse(command(4,1)).buffer[4]==255);close.cancel();CHECK(parse(command(4,1)).buffer[4]==0);});
  extra([]{auto close=PINEServer::BeginObserverExclusion(later());{auto other=PINEServer::BeginObserverExclusion(later());CHECK(other.poll()==State::rejected);}CHECK(parse(command(4,1)).buffer[4]==255);});
  extra([]{block_write=true;PINEServer::IPCBuffer reply;std::thread writer([&]{reply=parse(command(4,1));});{std::unique_lock<std::mutex> lock(control_mutex);control_cv.wait(lock,[]{return write_entered;});}auto close=PINEServer::BeginObserverExclusion(later());CHECK(close.poll()==State::draining);CHECK(parse(command(4,1)).buffer[4]==255);{std::lock_guard<std::mutex> lock(control_mutex);release_write=true;}control_cv.notify_one();writer.join();CHECK(reply.buffer[4]==0&&writes==1&&close.poll()==State::held);});
  auto observer_frame=[] {std::vector<u8> v{0xe0,1,0,0};v.resize(20);v[4]=1;for(u32 x:{1,0x100000,0x1000,4,0})append(v,x,4);return v;};
  extra([&]{immediate=true;auto reply=parse(observer_frame());CHECK(reply.buffer[4]==0&&reply.buffer[10]==static_cast<u8>(sh3::observer::Status::pause));auto close=PINEServer::BeginObserverExclusion(later());CHECK(snapshots==1&&close.poll()==State::held);});
  extra([&]{auto reply=parse(observer_frame());CHECK(reply.buffer[10]==static_cast<u8>(sh3::observer::Status::timeout));auto close=PINEServer::BeginObserverExclusion(later());CHECK(close.poll()==State::draining);pump();CHECK(snapshots==0&&close.poll()==State::held);});
  extra([&]{background=true;block_snapshot=true;auto reply=parse(observer_frame());CHECK(reply.buffer[10]==static_cast<u8>(sh3::observer::Status::timeout));auto close=PINEServer::BeginObserverExclusion(later());CHECK(close.poll()==State::draining);{std::lock_guard<std::mutex> lock(control_mutex);release_snapshot=true;}control_cv.notify_one();cpu_worker.join();CHECK(snapshots==1&&close.poll()==State::held);});
#endif
  reset();std::printf("{\"common_cases\":%u,\"exclusion_cases\":%u,\"result\":\"PASS\",\"effects_digest\":\"%016llx\"}\n",common_cases,exclusion_cases,static_cast<unsigned long long>(digest));
}
