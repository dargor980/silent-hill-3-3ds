// Own inter-thread Qt orchestration around SRC83's exact VU/GS fragments.
#include "joint_setup.inc"
#include <QThread>

class EmuThread : public QObject {
  Q_OBJECT
public:
  bool isOnEmuThread() const {return QThread::currentThread()==thread();}
public Q_SLOTS:
  void runOnCPUThread(const std::function<void()>&);
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
#include "cpu_slot.inc"
#include "cpu_dispatch.inc"
#include "ui_slot.inc"
#include "ui_dispatch.inc"

std::atomic_bool result_seen{false},producer_ran{false},ui_wait_entered{false};
std::atomic_uint window_effects{0};
std::atomic<std::int64_t> ui_wait_us{0};
std::weak_ptr<int> payload_lifetime;
void producer(const std::shared_ptr<int>& payload) {
  CHECK(g_emu_thread->isOnEmuThread());CHECK(*payload==173);
  CHECK(result_seen && !s_observer_pine_drain.active() && pine_gate.enter());
  CHECK(vu1Thread.GetObserverStatus({1,1})==Status::released);
  CHECK(MTGS::GetObserverStatus({1,1})==Status::released);
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
      QtHost::RunOnUIThread([payload,blocking=scenario=="cycle"]{
        CHECK(QThread::currentThread()==g_main_window->thread());ui_wait_entered=true;
        const auto begin=Clock::now();
        Host::RunOnCPUThread([payload]{producer(payload);},blocking);
        ui_wait_us=std::chrono::duration_cast<std::chrono::microseconds>(Clock::now()-begin).count();
        if(blocking)CHECK(producer_ran);
        else CHECK(!producer_ran);
      });
    }
    QtHost::RunOnUIThread([]{
      CHECK(QThread::currentThread()==g_main_window->thread());window_effects.fetch_add(1);
    },true);
    CHECK(window_effects==1);
  });payload.reset();
  queue(1,scenario=="cycle"?200ms:2000ms);CHECK(step()==State::draining);go.release();
  qt_pump(&loop);result_seen=true;
  CHECK(s_observer_pine_result.state==(scenario=="cycle"?State::timed_out:State::completed));
  // The queued CPU producer must be delivered before cleanup. In the cycle case
  // it is the event UI is waiting for; CPU's control pump has now retired tokens.
  if(scenario!="gs_ui"){
    auto end=Clock::now()+2s;
    while(!producer_ran){CHECK(Clock::now()<end);VMManager::Internal::BeforeObserverProducer();
      auto activity=VMManager::Internal::EnterObserverCpuActivity();loop.processEvents();}
  }
  // The provider may discard queued work on explicit shutdown. Finish the
  // producer's sentinel before closing, after all observer tokens are retired.
  MTGS::WaitGS(false);
  close_all();CHECK(window_effects==1);
  CHECK(callbacks==(scenario=="gs_ui"?0u:1u));
  CHECK(payload_lifetime.expired());
  g_emu_thread->moveToThread(QCoreApplication::instance()->thread());
  cpu_thread.quit();
}
int main(int argc,char** argv) {
  QCoreApplication app(argc,argv);CHECK(argc==2);std::string scenario=argv[1];
  CHECK(scenario=="gs_ui" || scenario=="queued" || scenario=="cycle");
  qRegisterMetaType<std::function<void()>>();
  QThread cpu_thread;EmuThread cpu_receiver;MainWindow ui_receiver;
  g_emu_thread=&cpu_receiver;g_main_window=&ui_receiver;cpu_receiver.moveToThread(&cpu_thread);
  QObject::connect(&cpu_thread,&QThread::finished,&app,&QCoreApplication::quit);
  cpu_thread.start();
  CHECK(QMetaObject::invokeMethod(&cpu_receiver,[&]{exercise(scenario,cpu_thread);},Qt::QueuedConnection));
  app.exec();CHECK(cpu_thread.wait(2000));CHECK(result_seen && window_effects==1);
  if(scenario=="cycle")CHECK(ui_wait_entered && ui_wait_us>0 && producer_ran);
  std::printf("{\"result\":\"PASS\",\"case\":\"%s\",\"ui_wait_us\":%lld}\n",argv[1],static_cast<long long>(ui_wait_us.load()));
}
#include "frontend.moc"
