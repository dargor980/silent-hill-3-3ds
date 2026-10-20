// Own inter-thread Qt orchestration around SRC83's exact VU/GS fragments.
#include "sh3_observer/external_waits.hpp"
namespace VMManager::Internal {sh3::observer::ExternalWaits::Wait ObserveExternalCpuWait(bool);}
#include "joint_setup.inc"
#include "external_scope.inc"
#include <QThread>

class EmuThread : public QObject {
  Q_OBJECT
public:
  bool isOnEmuThread() const {return QThread::currentThread()==thread();}
public Q_SLOTS:
  void runOnCPUThread(const std::function<void()>&);
  void closeInputSources();
  void reloadInputDevices();
};
class MainWindow : public QObject {
  Q_OBJECT
public Q_SLOTS:
  void runOnUIThread(const std::function<void()>&);
};
EmuThread* g_emu_thread{};
MainWindow* g_main_window{};
namespace Host {void RunOnCPUThread(std::function<void()>,bool=false);}
namespace QtHost {void RunOnUIThread(const std::function<void()>&,bool=false);}
std::atomic_uint device_reloads{0},device_closes{0};
namespace InputManager {
void ReloadDevices(){
  CHECK(g_emu_thread->isOnEmuThread() && !s_observer_pine_drain.active() && pine_gate.enter());
  CHECK(s_observer_external_waits.pending());
  CHECK(!VMManager::Internal::QueueObserverPineDrain(2,1s));
  device_reloads++;
}
void CloseSources(){device_closes++;}
}
#include "close_inputs.inc"
#include "reload_devices.inc"
#include "cpu_slot.inc"
#include "cpu_dispatch.inc"
#include "ui_slot.inc"
#include "ui_dispatch.inc"

std::atomic_bool result_seen{false},producer_ran{false},ui_wait_entered{false};
std::atomic_uint window_effects{0};
std::atomic<std::int64_t> ui_wait_us{0};
std::weak_ptr<int> payload_lifetime;
void producer(const std::shared_ptr<int>& payload,bool announced,bool early) {
  CHECK(g_emu_thread->isOnEmuThread());CHECK(*payload==173);
  CHECK(result_seen && !s_observer_pine_drain.active() && pine_gate.enter());
  CHECK(vu1Thread.GetObserverStatus({1,1})==Status::released);
  CHECK(MTGS::GetObserverStatus({1,1})==(early?Status::invalid:Status::released));
  CHECK(s_observer_external_waits.pending()==announced);
  if(announced)CHECK(!VMManager::Internal::QueueObserverPineDrain(2,1s));
  CHECK(!producer_ran.exchange(true));
  MTGS::RunOnGSThread([]{callbacks.fetch_add(1);});
}
void exercise(const std::string& scenario,QThread& cpu_thread) {
  CHECK(g_emu_thread->isOnEmuThread());s_observer_cpu_thread=true;s_observer_cpu_boundary.set_online(true);
  start();std::binary_semaphore go(0);QEventLoop loop;
  auto payload=std::make_shared<int>(173);payload_lifetime=payload;
  MTGS::RunOnGSThread([&,payload]{
    go.acquire();
    if(scenario!="gs_ui"){
      // This UI event is deliberately queued before GS's synchronous window request.
      QtHost::RunOnUIThread([payload,blocking=scenario=="cycle" || scenario=="early_cycle",direct=scenario=="direct_cycle",early=scenario=="early_cycle"]{
        CHECK(QThread::currentThread()==g_main_window->thread());ui_wait_entered=true;
        const auto begin=Clock::now();
        if(direct)g_emu_thread->closeInputSources();
        else Host::RunOnCPUThread([payload,blocking,early]{producer(payload,blocking,early);},blocking);
        ui_wait_us=std::chrono::duration_cast<std::chrono::microseconds>(Clock::now()-begin).count();
        if(blocking)CHECK(producer_ran);
        else if(direct)CHECK(device_reloads==1 && device_closes==0);
        else CHECK(!producer_ran);
      });
    }
    QtHost::RunOnUIThread([]{
      CHECK(QThread::currentThread()==g_main_window->thread());window_effects.fetch_add(1);
    },true);
    CHECK(window_effects==1);
  });payload.reset();
  queue(1,2000ms);CHECK(step()==State::draining);
  // Establish both accepted tokens before allowing UI to announce its wait.
  // Otherwise priority cancellation can legitimately precede the GS request.
  if(scenario!="early_cycle"){
    until([]{CHECK(step()==State::draining);return MTGS::GetObserverStatus({1,1})==Status::pending;});
    CHECK(vu1Thread.GetObserverStatus({1,1})==Status::held);
  }
  go.release();
  if(scenario=="early_cycle")until([]{return s_observer_external_waits.pending();});
  qt_pump(&loop);result_seen=true;
  CHECK(s_observer_pine_result.state==((scenario=="cycle" || scenario=="direct_cycle" || scenario=="early_cycle")?State::cancelled:State::completed));
  // The queued CPU producer must be delivered before cleanup. In the cycle case
  // it is the event UI is waiting for; CPU's control pump has now retired tokens.
  if(scenario!="gs_ui"){
    auto end=Clock::now()+2s;
    while(!producer_ran && !device_reloads){CHECK(Clock::now()<end);VMManager::Internal::BeforeObserverProducer();
      auto activity=VMManager::Internal::EnterObserverCpuActivity();loop.processEvents();}
  }
  // The provider may discard queued work on explicit shutdown. Finish the
  // producer's sentinel before closing, after all observer tokens are retired.
  MTGS::WaitGS(false);
  until([]{return !s_observer_external_waits.pending();});
  CHECK(VMManager::Internal::QueueObserverPineDrain(2,2s));qt_pump(&loop);
  CHECK(s_observer_pine_result.state==State::completed);
  close_all();CHECK(window_effects==1);
  CHECK(callbacks==((scenario=="gs_ui" || scenario=="direct_cycle")?0u:1u));
  CHECK(payload_lifetime.expired());
  g_emu_thread->moveToThread(QCoreApplication::instance()->thread());
  cpu_thread.quit();
}
void edge(const std::string& scenario,QThread& cpu_thread) {
  CHECK(g_emu_thread->isOnEmuThread());s_observer_cpu_thread=true;s_observer_cpu_boundary.set_online(true);
  start();QEventLoop loop;auto payload=std::make_shared<int>(173);payload_lifetime=payload;
  if(scenario=="inline"){
    queue(1,2s);wait_held();
    Host::RunOnCPUThread([payload]{
      CHECK(*payload==173 && !s_observer_external_waits.pending());
      CHECK(!s_observer_pine_drain.active() && pine_gate.enter());
      CHECK(s_observer_pine_result.state==State::cancelled);
      CHECK(!producer_ran.exchange(true));
    },true);
    g_emu_thread->closeInputSources();CHECK(device_closes==1 && device_reloads==0);
  }else{
    auto prior=pine_gate.enter();CHECK(prior);queue(1,2s);
    CHECK(step()==State::draining && !s_observer_pine_drain.effects_started());
    QtHost::RunOnUIThread([payload]{
      Host::RunOnCPUThread([payload]{
        CHECK(*payload==173 && s_observer_external_waits.pending());
        CHECK(!s_observer_pine_drain.active() && pine_gate.enter());
        CHECK(s_observer_pine_result.state==State::cancelled);
        CHECK(vu1Thread.GetObserverStatus({1,1})==Status::invalid);
        CHECK(MTGS::GetObserverStatus({1,1})==Status::invalid);
        CHECK(!VMManager::Internal::QueueObserverPineDrain(2,1s));
        CHECK(!producer_ran.exchange(true));
      },true);
      CHECK(producer_ran);
    });
    until([]{return s_observer_external_waits.pending();});
    if(scenario=="pine_poll")qt_pump(&loop);
    else VMManager::Internal::BeforeObserverProducer();
    CHECK(!s_observer_pine_drain.active() && s_observer_pine_result.state==State::cancelled);
    while(!producer_ran){auto activity=VMManager::Internal::EnterObserverCpuActivity();loop.processEvents();}
  }
  payload.reset();until([]{return !s_observer_external_waits.pending() && payload_lifetime.expired();});
  CHECK(producer_ran && VMManager::Internal::QueueObserverPineDrain(2,2s));qt_pump(&loop);
  CHECK(s_observer_pine_result.state==State::completed);result_seen=true;
  close_all();g_emu_thread->moveToThread(QCoreApplication::instance()->thread());cpu_thread.quit();
}
int main(int argc,char** argv) {
  QCoreApplication app(argc,argv);CHECK(argc==2);std::string scenario=argv[1];
  const bool edge_case=scenario=="inline" || scenario=="pine_poll" || scenario=="pine_before";
  CHECK(edge_case || scenario=="gs_ui" || scenario=="queued" || scenario=="cycle" || scenario=="direct_cycle" || scenario=="early_cycle");
  qRegisterMetaType<std::function<void()>>();
  QThread cpu_thread;EmuThread cpu_receiver;MainWindow ui_receiver;
  g_emu_thread=&cpu_receiver;g_main_window=&ui_receiver;cpu_receiver.moveToThread(&cpu_thread);
  QObject::connect(&cpu_thread,&QThread::finished,&app,&QCoreApplication::quit);
  cpu_thread.start();
  CHECK(QMetaObject::invokeMethod(&cpu_receiver,[&]{if(edge_case)edge(scenario,cpu_thread);else exercise(scenario,cpu_thread);},Qt::QueuedConnection));
  app.exec();CHECK(cpu_thread.wait(2000));CHECK(result_seen && window_effects==(edge_case?0u:1u));
  if(scenario=="cycle" || scenario=="early_cycle")CHECK(ui_wait_entered && ui_wait_us>0 && producer_ran);
  if(scenario=="direct_cycle")CHECK(ui_wait_entered && device_reloads==1 && !producer_ran);
  std::printf("{\"result\":\"PASS\",\"case\":\"%s\",\"ui_wait_us\":%lld}\n",argv[1],static_cast<long long>(ui_wait_us.load()));
}
#include "frontend.moc"
