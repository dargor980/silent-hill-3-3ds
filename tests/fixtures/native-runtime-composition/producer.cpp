// Native inventory and socket integration. Host/CPU facts below are test doubles.
#include "sh3_observer/macos_diagnostic_work.hpp"
#include "sh3_observer/macos_diagnostic_sink.hpp"
#include "sh3_observer/macos_image_identity.hpp"
#include "sh3_observer/runtime_diagnostic_session.hpp"
#include <algorithm>
#include <atomic>
#include <cstdio>
#include <cstdlib>
#include <cstring>
#include <functional>
#include <mach-o/dyld.h>
#include <mutex>
#include <pthread.h>
#include <string>
#include <sys/stat.h>
#include <sys/un.h>
#include <thread>
#include <unistd.h>
#include <vector>
using namespace sh3::observer;
using Clock=DiagnosticClock::Clock;using Reason=DiagnosticRejection;using namespace std::chrono_literals;
static void check(bool value,const char* why){if(!value){std::fprintf(stderr,"NR_FAIL %s\n",why);std::abort();}}
static std::uint64_t tid(){std::uint64_t id{};check(pthread_threadid_np(nullptr,&id)==0,"tid");return id;}
static bool parse(const char* text,Sha256& out){out={};if(!text||std::strlen(text)!=64)return false;for(unsigned i=0;i<64;++i){const char c=text[i];unsigned d{};if(c>='0'&&c<='9')d=c-'0';else if(c>='a'&&c<='f')d=c-'a'+10;else return false;out[i/2]|=static_cast<std::uint8_t>(d<<(i%2?0:4));}return true;}
static void event(const char* phase){std::fprintf(stderr,"NR_EVENT phase=%s\n",phase);std::fflush(stderr);}
using Fds=std::vector<std::array<std::uint64_t,4>>;
static Fds descriptors(){Fds out;for(int fd=0;fd<1024;++fd){struct stat s{};if(::fstat(fd,&s)==0)out.push_back({static_cast<std::uint64_t>(fd),static_cast<std::uint64_t>(s.st_dev),s.st_ino,static_cast<std::uint64_t>(s.st_mode)});}return out;}

struct CpuDouble {
 const std::string mode;RuntimeRevocation generation;std::mutex mutex;std::function<void()> callback;
 std::atomic<std::uint64_t> owner{};std::atomic<bool> execute{},retire{},retired{};std::atomic<unsigned> acquired{};
 std::shared_ptr<RuntimeDiagnosticTicket> ticket;std::thread thread;
 explicit CpuDouble(std::string name):mode(std::move(name)){}
 void start(){thread=std::thread([this]{
  owner=tid();std::function<void()> task;const auto limit=Clock::now()+8s;
  while(!task){check(Clock::now()<limit,"CPU callback absent");{std::lock_guard lock(mutex);if(callback)task=std::move(callback);}if(!task)std::this_thread::sleep_for(1ms);}
  while(!execute.load()){check(Clock::now()<limit,"CPU callback unreleased");std::this_thread::sleep_for(1ms);}
  task();
  while(!retire.load()){check(Clock::now()<limit,"CPU retirement unreleased");std::this_thread::sleep_for(1ms);}
  if(ticket)check(ticket->retire(),"CPU retirement");retired=true;
 });}
 std::shared_ptr<RuntimeDiagnosticTicket> queue(std::uint64_t id,Clock::time_point deadline)noexcept{
  check(tid()==owner.load()&&id>0,"CPU identity");if(mode=="queue_rejected")return {};
  check(deadline>Clock::now(),"late acquisition");++acquired;
  ticket=make_runtime_diagnostic_ticket(generation);check(bool(ticket),"ticket");
  RuntimeDiagnosticSnapshot value;value.scope_id=id;value.deadline=deadline;value.epochs={11,12,13,14};
  for(auto key:{AdmissionCondition::cpu_thread,AdmissionCondition::cpu_boundary,AdmissionCondition::paused,
      AdmissionCondition::pine_excluded,AdmissionCondition::gs_drained,AdmissionCondition::vu_drained})
    value.facts[static_cast<std::size_t>(key)]=AdmissionFact::satisfied;
  value.facts[static_cast<std::size_t>(AdmissionCondition::vif_dynarec_disabled)]=AdmissionFact::violated;
  check(ticket->publish(value),"ticket publication");return ticket;
 }
 void finish(){execute=true;retire=true;thread.join();check(retired.load(),"CPU not retired");}
};
static CpuDouble* actor{};
namespace FixtureHost {
static void RunOnCPUThread(std::function<void()> task,bool block){check(actor&&!block,"blocking dispatch");std::lock_guard lock(actor->mutex);check(!actor->callback,"duplicate dispatch");actor->callback=std::move(task);}
}
namespace FixtureVMManager::Internal {
static bool IsObserverCpuThread(){return actor&&actor->owner.load()==tid();}
static std::shared_ptr<RuntimeDiagnosticTicket> QueueObserverRuntimeDiagnosticUntil(std::uint64_t id,Clock::time_point deadline)noexcept{return actor->queue(id,deadline);}
}
// Include the unmodified own frontend, explicitly substituting its two ports.
#define Host FixtureHost
#define VMManager FixtureVMManager
#include "runtime_frontend.inc"
#undef VMManager
#undef Host

struct Fault final:InspectionControl {
 const std::string mode;std::atomic<bool> entered{},release{};std::atomic<std::uint64_t> worker{};unsigned reads{};
 explicit Fault(std::string name):mode(std::move(name)){}
 bool checkpoint(InspectionStep step)noexcept override{
  const auto id=tid(),previous=worker.exchange(id);check(!previous||previous==id,"DW identity");
  if(step==InspectionStep::file_read&&++reads==6&&mode.find("_read")!=std::string::npos){
   entered=true;event("work");const auto limit=Clock::now()+7s;
   while(!release.load()){check(Clock::now()<limit,"DW unreleased");std::this_thread::sleep_for(1ms);}
  }return true;
 }
};
struct Channel final:DiagnosticChannel {
 MacOSDiagnosticSink native;RuntimeDiagnosticHandoff& handoff;CpuDouble& cpu;const std::string mode;
 unsigned received{},bytes{},zero{},writes{},closes{};bool injected{},announced{};
 Channel(int fd,MacOSPeerIdentity expected,RuntimeDiagnosticHandoff& h,CpuDouble& c,std::string n)
  :native(fd,expected),handoff(h),cpu(c),mode(std::move(n)){}
 bool connected()noexcept override{return native.connected();}
 bool read(std::uint8_t* out,std::size_t size,std::size_t& got,Clock::duration wait)noexcept override{
  const bool ok=native.read(out,std::min(size,mode=="fragmented"?std::size_t(3):size),got,wait);received+=got;
  if(!injected&&received>32){
   if(mode=="revoke_between"){injected=true;cpu.generation.advance();}
   if(mode=="deadline_second"){injected=true;std::this_thread::sleep_for(2200ms);}
  }return ok;
 }
 bool write(const std::uint8_t* input,std::size_t size,std::size_t& sent,Clock::duration wait)noexcept override{
  ++writes;sent=0;
  if(!injected&&bytes>0&&(mode=="cancel_send"||mode=="revoke_send")){
   injected=true;if(mode=="cancel_send")handoff.cancel();else cpu.generation.advance();return true;
  }
  const auto chunk=mode=="fragmented"?3u:mode=="backpressure_resume"?1u:mode.find("_send")!=std::string::npos?17u:294u;
  const bool ok=native.write(input,std::min(size,static_cast<std::size_t>(chunk)),sent,wait);bytes+=sent;
  if(ok&&!sent){++zero;if(!announced){announced=true;event("backpressure");}}
  return ok;
 }
 bool close()noexcept override{++closes;return native.close();}
};
static void survey(){
 std::fprintf(stderr,"NR_TRACE survey_entered\n");std::fflush(stderr);
 const auto before=descriptors();const auto io=tid();
 const char* name=std::getenv("SH3_WORK_CONTROL"),*endpoint=std::getenv("SH3_ENDPOINT"),*path=std::getenv("SH3_LAUNCH_MANIFEST");
 DiagnosticExpectation expectation{IdentityProfile::macos_platform_slices_v2,{},{},{}};
 check(name&&endpoint&&path&&parse(std::getenv("SH3_POLICY"),expectation.policy_evidence)&&parse(std::getenv("SH3_LAUNCH_MANIFEST_SHA256"),expectation.application_evidence)&&parse(std::getenv("SH3_PLATFORM"),expectation.platform_evidence),"configuration");
 const std::string mode(name);CpuDouble cpu(mode);actor=&cpu;cpu.start();
 const auto start=Clock::now(),deadline=start+5s;
 const int fd=::socket(AF_UNIX,SOCK_STREAM,0);check(fd>=0,"socket");sockaddr_un address{};address.sun_family=AF_UNIX;
 check(std::strlen(endpoint)<sizeof(address.sun_path),"endpoint");std::strcpy(address.sun_path,endpoint);
 check(::connect(fd,reinterpret_cast<sockaddr*>(&address),sizeof(address))==0,"connect");
 MacOSPeerIdentity peer;check(read_macos_peer(fd,peer)&&peer.pid==static_cast<unsigned>(::getppid())&&peer.birth_ns==read_macos_birth(::getppid())&&peer.euid==::geteuid()&&peer.ruid==::getuid(),"parent identity");
 if(mode=="backpressure_resume"){int size=1024;check(::setsockopt(fd,SOL_SOCKET,SO_SNDBUF,&size,sizeof(size))==0&&::setsockopt(fd,SOL_SOCKET,SO_SNDLOWAT,&size,sizeof(size))==0,"socket buffers");}
 auto handoff=pcsx2::queue_runtime_diagnostic(deadline);check(bool(handoff)&&handoff->deadline()==deadline,"frontend handoff");
 if(mode=="wrong_producer_peer")peer.token[0]^=1;
 Channel channel(fd,peer,*handoff,cpu,mode);Fault fault(mode);MacOSDiagnosticDetails detail;
 if(mode=="cancel_before_callback")handoff->cancel();
 if(mode!="cancel_before_callback"&&mode!="deadline_queue")cpu.execute=true;
 std::shared_ptr<RuntimeDiagnosticBinding> binding;
 while(handoff->failure()==Reason::none&&!(binding=handoff->binding())){
  if(!channel.connected()){handoff->cancel(Reason::peer_lost);break;}
  std::this_thread::sleep_for(1ms);
 }
 std::unique_ptr<DiagnosticWorker> worker;std::unique_ptr<RuntimeDiagnosticSession> session;
 unsigned confirmed{};bool pending_cpu{},pending_work{};Reason reason=handoff->failure();
 if(binding){
  MacOSDiagnosticConfiguration config{path,expectation,reinterpret_cast<std::uintptr_t>(_dyld_get_image_header(0))};
  worker=make_runtime_diagnostic_worker(expectation,std::make_unique<MacOSDiagnosticWorkFactory>(config,&fault,&detail),binding);
  check(bool(worker),"DW construction");session=std::make_unique<RuntimeDiagnosticSession>(*handoff,*worker,channel);
  while(confirmed<3){
   if(fault.entered.load()){
    if(mode=="lifecycle_read")cpu.generation.advance();
    if(mode=="producer_cancel_read")handoff->cancel();
   }
   const auto result=session->step();
   if(result==RuntimeSessionResult::rejected)break;
   if(result==RuntimeSessionResult::complete){++confirmed;std::fprintf(stderr,"NR_DELIVERY sequence=%u elapsed_ns=%lld\n",confirmed,static_cast<long long>(std::chrono::duration_cast<std::chrono::nanoseconds>(Clock::now()-start).count()));}
   if(result==RuntimeSessionResult::waiting)std::this_thread::sleep_for(1ms);
  }
  if(confirmed==3){const auto limit=Clock::now()+1s;while(channel.connected()&&Clock::now()<limit)std::this_thread::sleep_for(1ms);}
  reason=session->failure();
  pending_cpu=session->close_until(Clock::now()+1ms)==RuntimeSessionClose::pending;
  check(!worker->status().joined,"DW joined before CPU retirement");
 }else{
  handoff->cancel();check(channel.close(),"early channel close");
  pending_cpu=!wait_runtime_diagnostic_stopped(*handoff,nullptr,Clock::now());
 }
 cpu.finish();actor=nullptr;check(handoff->quiescent(),"CPU acknowledgement");
 if(worker){
  if(fault.entered.load()){
   pending_work=session->close_until(Clock::now()+1ms)==RuntimeSessionClose::pending;
   check(pending_work&&!worker->status().joined,"blocked DW prematurely joined");
  }
  fault.release=true;check(session->close_until(Clock::now()+3s)==RuntimeSessionClose::closed,"session close");
  check(worker->status().joined&&worker->status().cleanup_verified,"DW cleanup");
 }
 if(reason==Reason::none)reason=handoff->failure();
 const auto worker_id=fault.worker.load();check(cpu.owner!=io&&(!worker_id||(worker_id!=io&&worker_id!=cpu.owner)),"thread separation");
 check(channel.closes==1,"socket closed more than once");
 std::fprintf(stderr,"NR_DETAIL manifest=%u origins=%u inventory=%u prepared=%u sampled=%u closed=%u\n",static_cast<unsigned>(detail.manifest),static_cast<unsigned>(detail.origins),static_cast<unsigned>(detail.inventory),detail.prepared,detail.sampled,detail.closed);
 std::fprintf(stderr,"NR_END case=%s confirmed=%u reason=%u received=%u bytes=%u zero=%u acquired=%u cpu_retired=%u joined=%u work_closed=%u sink_closed=%u same_fds=%u io=%llu cpu=%llu worker=%llu pending_cpu=%u pending_work=%u injected=%u admitted=0\n",name,confirmed,static_cast<unsigned>(reason),channel.received,channel.bytes,channel.zero,cpu.acquired.load(),cpu.retired.load(),worker?worker->status().joined:true,worker?worker->status().cleanup_verified:true,channel.closes==1,before==descriptors(),static_cast<unsigned long long>(io),static_cast<unsigned long long>(cpu.owner.load()),static_cast<unsigned long long>(worker_id),pending_cpu,pending_work,fault.entered.load()||channel.injected);
}
__attribute__((constructor))static void initialize(){std::fprintf(stderr,"NR_TRACE initialized\n");std::fflush(stderr);ImageSnapshot snapshot;check(MacOSImageEvents::read(snapshot),"image registry");check(std::atexit(survey)==0,"atexit");}
