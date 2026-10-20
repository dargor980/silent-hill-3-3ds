// Own QtCore integration probe; no VM, socket or provider function bodies.
#include "check.hpp"
#include "sh3_observer/pine_drain.hpp"
#include <QCoreApplication>
#include <QEventLoop>
#include <QTimer>
#include <cstdio>
using namespace sh3::observer;
using S=PineDrain::State;
struct Source final : BarrierSource {
  CooperativeGate gate;
  CooperativeGate::Closure close(CooperativeGate::Clock::time_point deadline) noexcept override {
    return gate.close(deadline);
  }
};
int main(int argc,char** argv) {
  QCoreApplication app(argc,argv);
  unsigned total_iterations=0, effects=0;
  const auto started=PineDrain::Clock::now();
  for(unsigned scenario=0;scenario<4;++scenario) {
    CpuBoundary cpu; cpu.set_online(true); Source source; PineDrain drain(cpu,source);
    QEventLoop loop; auto work=source.gate.enter(); CHECK(work);
    // A real queued callback wakes the paused loop after submitting, before admission.
    QTimer::singleShot(0,&loop,[&] {
      CHECK(!cpu.at_boundary());
      CHECK(drain.submit({1,{1,1},PineDrain::Clock::now()+std::chrono::milliseconds(scenario==1?30:2000)}));
      loop.quit();
    });
    { auto dispatch=cpu.activity(); loop.exec(); }
    if(scenario==0) {
      QTimer::singleShot(0,&loop,[work,&effects] { CHECK(work); ++effects; }); work={};
    } else if(scenario==2) {
      QTimer::singleShot(0,&loop,[&] { CHECK(drain.cancel(1)); });
    } else if(scenario==3) {
      auto* context=new QObject;
      QTimer::singleShot(60000,context,[work] { CHECK(work); CHECK(false); }); work={};
      delete context; // Qt destroys the retained callback without running it.
    }
    unsigned iterations=0;
    while(drain.active()) {
      CHECK(++iterations<5000);
      auto root=cpu.enter(); CHECK(root.valid());
      const auto state=drain.step(true,{1,1});
      if(state==S::held) CHECK(drain.complete(true,{1,1}));
      if(state!=S::draining) {
        const auto result=drain.retire();
        CHECK(result.state==(scenario==1?S::timed_out:scenario==2?S::cancelled:S::completed));
        CHECK(source.gate.enter()); break;
      }
      CHECK(!source.gate.enter());
      auto dispatch=cpu.activity(); CHECK(!root.valid());
      QTimer timer; timer.setSingleShot(true);
      QObject::connect(&timer,&QTimer::timeout,&loop,&QEventLoop::quit);
      timer.start(1); loop.exec();
    }
    CHECK(!drain.active()); total_iterations+=iterations;
  }
  CHECK(effects==1);
  const auto elapsed=std::chrono::duration_cast<std::chrono::microseconds>(PineDrain::Clock::now()-started).count();
  std::printf("{\"cases\":4,\"result\":\"PASS\",\"iterations\":%u,\"elapsed_us\":%lld,\"qt\":\"%s\"}\n",
    total_iterations,static_cast<long long>(elapsed),qVersion());
}
