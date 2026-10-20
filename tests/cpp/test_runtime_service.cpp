// Service and native channel are real; CPU queue and VM snapshot are doubles.
#include "check.hpp"
#include "runtime_service.hpp"
#include "runtime_frontend.hpp"
#include <atomic>
#include <chrono>
#include <cstdio>
#include <cstdlib>
#include <string>
#include <thread>
using namespace sh3::observer;
using namespace sh3::observer::pcsx2;
using namespace std::chrono_literals;
using Clock=DiagnosticClock::Clock;
static std::string mode;
static std::atomic<unsigned> requests{},acquisitions{};
static std::atomic<bool> release_cpu{},cancel_seen{},callback_ready{},run_callback{};
static std::thread cpu;
static std::shared_ptr<RuntimeDiagnosticHandoff> retained;
static RuntimeRevocation generation;
template<class F>void eventually(F f){
  const auto until=Clock::now()+8s;
  while(!f()){CHECK(Clock::now()<until);std::this_thread::sleep_for(1ms);}
}
struct Queue final:RuntimeDiagnosticQueue {
  std::shared_ptr<RuntimeDiagnosticTicket> queue_until(std::uint64_t id,Clock::time_point deadline)noexcept override{
    CHECK(id==1);++acquisitions;
    if(mode=="queue_rejected")return {};
    auto ticket=make_runtime_diagnostic_ticket(generation);
    RuntimeDiagnosticSnapshot s;s.scope_id=id;s.deadline=deadline;s.epochs={1,2,3,4};
    for(auto k:{AdmissionCondition::cpu_thread,AdmissionCondition::cpu_boundary,AdmissionCondition::paused,
        AdmissionCondition::pine_excluded,AdmissionCondition::vu_drained,AdmissionCondition::gs_drained})
      s.facts[static_cast<std::size_t>(k)]=AdmissionFact::satisfied;
    CHECK(ticket->publish(s));
    if(mode=="disconnect"){std::puts("RT_CPU_READY");std::fflush(stdout);}
    owner=ticket;return ticket;
  }
  std::shared_ptr<RuntimeDiagnosticTicket> owner;
};
namespace sh3::observer::pcsx2 {
std::shared_ptr<RuntimeDiagnosticHandoff> queue_runtime_diagnostic(Clock::time_point deadline)noexcept{
  ++requests;
  if(mode=="queue_null")return {};
  retained=std::make_shared<RuntimeDiagnosticHandoff>(1,deadline);
  auto request=retained;
  cpu=std::thread([request]{
    Queue q;callback_ready=true;
    if(mode=="late_callback")eventually([]{return run_callback.load();});
    request->execute(q);
    if(q.owner){
      eventually([&]{return request->failure()!=DiagnosticRejection::none;});
      cancel_seen=true;
      eventually([]{return release_cpu.load();});
      CHECK(q.owner->retire());
    }
  });
  return request;
}
}
int main(int argc,char** argv){
  CHECK(argc==2);mode=argv[1];
  if(mode=="ui_policy"){
    using Action=RuntimeServiceUIAction;RuntimeVMShutdownRequest out{true,true,true};
    RuntimeUIIntent inactive;CHECK(!inactive.request_vm({}) && !inactive.request_exit());
    CHECK(inactive.consume(out)==Action::none && !out.allow_confirm);
    for(unsigned bits=0;bits<8;++bits){
      const RuntimeVMShutdownRequest first{bool(bits&1),bool(bits&2),bool(bits&4)};
      RuntimeUIIntent policy;policy.start();CHECK(policy.request_vm(first));
      CHECK(policy.request_vm({!first.allow_confirm,!first.allow_save_to_state,!first.default_save_to_state}));
      CHECK(policy.consume(out)==Action::shutdown_vm && !policy.active());
      CHECK(out.allow_confirm==first.allow_confirm && out.allow_save_to_state==first.allow_save_to_state && out.default_save_to_state==first.default_save_to_state);
      CHECK(policy.consume(out)==Action::none && !policy.request_vm(first) && !policy.request_exit());
    }
    for(bool deferred:{false,true}){
      RuntimeUIIntent policy;policy.start();if(deferred)CHECK(policy.request_vm({true,true,true}));
      CHECK(policy.request_exit() && policy.request_exit() && policy.request_vm({true,true,true}));
      CHECK(policy.consume(out)==Action::exit_application && !out.allow_confirm && !out.allow_save_to_state && !out.default_save_to_state);
      CHECK(policy.consume(out)==Action::none);
    }
    RuntimeUIIntent automatic;automatic.start();CHECK(automatic.consume(out)==Action::exit_application);return 0;
  }
  CHECK(!cancel_runtime_service_from_ui());
  const auto result=start_runtime_service();
  if(mode=="disabled" || mode=="bad_hash" || mode=="zero_hash" || mode=="bad_trigger" ||
      mode=="relative" || mode=="missing_field" || mode=="long_endpoint"){
    CHECK(result==(mode=="disabled"?RuntimeServiceStart::disabled:RuntimeServiceStart::failed));
    CHECK(!cancel_runtime_service_from_ui());
    CHECK(runtime_service_finished() && finish_runtime_service() && requests==0);return 0;
  }
  CHECK(result==RuntimeServiceStart::started);
  CHECK(start_runtime_service()==RuntimeServiceStart::failed);
  if(mode=="cancel_wait" || mode=="paused" || mode=="ui_wait" || mode=="ui_vm_wait"){
    std::this_thread::sleep_for(30ms);CHECK(requests==0 && !runtime_service_finished());
    if(mode=="ui_vm_wait"){
      CHECK(defer_runtime_vm_shutdown({true,false,false}));CHECK(defer_runtime_vm_shutdown({false,true,true}));
    }else if(mode=="ui_wait"){
      CHECK(cancel_runtime_service_from_ui());CHECK(cancel_runtime_service_from_ui());
    }else if(mode=="cancel_wait")cancel_runtime_service();else notify_runtime_service_paused();
  }
  if(mode=="late_callback"){
    eventually([]{return callback_ready.load();});cancel_runtime_service();
    eventually([]{return runtime_service_finished();});
    CHECK(acquisitions==0);run_callback=true;
  }else if(mode=="missing_manifest" || mode=="paused" || mode=="disconnect" || mode=="cancel_session" || mode=="ui_session" || mode=="ui_finished" || mode=="ui_vm_session"){
    if(mode=="cancel_session" || mode=="ui_session" || mode=="ui_vm_session"){
      eventually([]{return acquisitions.load()>0;});
      if(mode=="ui_vm_session"){
        CHECK(defer_runtime_vm_shutdown({true,false,false}));CHECK(defer_runtime_vm_shutdown({false,true,true}));
      }else if(mode=="ui_session"){
        CHECK(cancel_runtime_service_from_ui());CHECK(cancel_runtime_service_from_ui());
      }else cancel_runtime_service();
    }
    eventually([]{return cancel_seen.load();});
    CHECK(!runtime_service_finished() && !finish_runtime_service());
    RuntimeVMShutdownRequest pending;CHECK(poll_runtime_service_ui(pending)==RuntimeServiceUIAction::none);
    std::this_thread::sleep_for(20ms);CHECK(!runtime_service_finished());release_cpu=true;
  }
  eventually([]{return runtime_service_finished();});CHECK(finish_runtime_service());
  if(mode=="ui_vm_wait" || mode=="ui_vm_session"){
    RuntimeVMShutdownRequest request;CHECK(poll_runtime_service_ui(request)==RuntimeServiceUIAction::shutdown_vm);
    CHECK(request.allow_confirm && !request.allow_save_to_state && !request.default_save_to_state);
    CHECK(!cancel_runtime_service_from_ui() && !defer_runtime_vm_shutdown({}));
    CHECK(poll_runtime_service_ui(request)==RuntimeServiceUIAction::none);
  }
  if(mode=="ui_finished"){
    CHECK(cancel_runtime_service_from_ui());CHECK(cancel_runtime_service_from_ui());
    CHECK(runtime_service_finished());
  }
  if(cpu.joinable())cpu.join();
  CHECK(finish_runtime_service());
  if(mode=="cancel_wait" || mode=="ui_wait" || mode=="ui_vm_wait" || mode=="connect_failure")CHECK(requests==0);
  else CHECK(requests==1);
  if(retained)CHECK(retained->quiescent());
}
