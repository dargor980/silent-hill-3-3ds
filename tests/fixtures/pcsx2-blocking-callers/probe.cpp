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


#include <mutex>
std::atomic_bool completed{false},ui_returned{false},retired_before_callback{false};
std::atomic_bool observed_contention{false};
std::atomic_uint delivered{0};
std::mutex resource;
std::binary_semaphore resource_ready(0),callback_entered(0);
void exercise_lock(bool contended,QThread& cpu_thread) {
  s_observer_cpu_thread=true;s_observer_cpu_boundary.set_online(true);start();
  std::thread adversary;
  if(contended){
    adversary=std::thread([]{
      std::unique_lock held(resource);resource_ready.release();callback_entered.acquire();
      CHECK(retired_before_callback && observed_contention);
      CHECK(s_observer_external_waits.pending() && !completed && !ui_returned);
      // Only this thread owns/unlocks the real mutex. The controlled adversary
      // ends its delay after proving the observer's retirement is insufficient.
      held.unlock();
    });
    resource_ready.acquire();
  }
  auto payload=std::make_shared<int>(281);std::weak_ptr<int> weak=payload;
  queue(1,2s);wait_held();QEventLoop loop;
  QtHost::RunOnUIThread([payload,contended]{
    Host::RunOnCPUThread([payload,contended]{
      CHECK(g_emu_thread->isOnEmuThread() && *payload==281);
      CHECK(s_observer_external_waits.pending() && !s_observer_pine_drain.active());
      CHECK(s_observer_pine_result.state==State::cancelled && pine_gate.enter());
      CHECK(vu1Thread.GetObserverStatus({1,1})==Status::released);
      CHECK(MTGS::GetObserverStatus({1,1})==Status::released);
      retired_before_callback=true;
      const bool acquired=resource.try_lock();observed_contention=!acquired;
      CHECK(acquired!=contended);if(acquired)resource.unlock();
      if(contended)callback_entered.release();
      std::unique_lock lock(resource);
      CHECK(delivered.fetch_add(1)==0);completed=true;
    },true);
    CHECK(completed && delivered==1 && !s_observer_external_waits.pending());
    ui_returned=true;
  });payload.reset();
  until([]{return s_observer_external_waits.pending();});qt_pump(&loop);
  CHECK(s_observer_pine_result.state==State::cancelled && !s_observer_pine_drain.active());
  VMManager::Internal::BeforeObserverProducer();
  {auto activity=VMManager::Internal::EnterObserverCpuActivity();loop.processEvents();}
  until([&]{return ui_returned && weak.expired();});
  if(adversary.joinable())adversary.join();
  CHECK(completed && retired_before_callback && delivered==1 && observed_contention==contended);
  CHECK(VMManager::Internal::QueueObserverPineDrain(2,2s));qt_pump(&loop);
  CHECK(s_observer_pine_result.state==State::completed);close_all();
  g_emu_thread->moveToThread(QCoreApplication::instance()->thread());cpu_thread.quit();
}
int main(int argc,char** argv){
  QCoreApplication app(argc,argv);CHECK(argc==2);std::string scenario=argv[1];
  CHECK(scenario=="free" || scenario=="contended");
  qRegisterMetaType<std::function<void()>>();QThread cpu_thread;EmuThread cpu_receiver;MainWindow ui_receiver;
  g_emu_thread=&cpu_receiver;g_main_window=&ui_receiver;cpu_receiver.moveToThread(&cpu_thread);
  QObject::connect(&cpu_thread,&QThread::finished,&app,&QCoreApplication::quit);cpu_thread.start();
  CHECK(QMetaObject::invokeMethod(&cpu_receiver,[&]{exercise_lock(scenario=="contended",cpu_thread);},Qt::QueuedConnection));
  app.exec();CHECK(cpu_thread.wait(2000) && completed && ui_returned && delivered==1);
  std::printf("{\"result\":\"PASS\",\"case\":\"%s\",\"contended\":%s}\n",argv[1],observed_contention?"true":"false");
}
#include "frontend.moc"
