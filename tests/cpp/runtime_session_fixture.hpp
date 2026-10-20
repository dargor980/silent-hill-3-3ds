#pragma once
#include "delivery_fixture.hpp"
#include "sh3_observer/runtime_diagnostic_session.hpp"
#include <algorithm>
#include <vector>

namespace session_fixture {
using namespace delivery_fixture;
using Result=RuntimeSessionResult;
using Closed=RuntimeSessionClose;
inline auto packet(std::uint64_t sequence=1) {
  std::array<std::uint8_t,diagnostic_request_size> p{};
  const char magic[]="SH3PDQ02";std::copy_n(magic,8,p.begin());
  std::fill_n(p.begin()+8,16,1);
  for(unsigned i=0;i<8;++i)p[24+i]=static_cast<std::uint8_t>(sequence>>(i*8));
  return p;
}
// Real CPU and DW threads; CPU queue/snapshot and inventory are explicit doubles.
struct Runtime final : RuntimeDiagnosticQueue {
  DiagnosticClock& clock;RuntimeRevocation generation;
  RuntimeDiagnosticHandoff handoff;
  std::shared_ptr<RuntimeDiagnosticTicket> ticket;
  std::atomic<bool> ready{},retire{};
  State work;
  std::unique_ptr<DiagnosticWorker> worker;
  std::thread cpu;
  explicit Runtime(DiagnosticClock& c):clock(c),handoff(1,c.now()+5s,c),cpu([this]{
    CHECK(handoff.execute(*this));
    RuntimeDiagnosticSnapshot s;s.scope_id=7;s.deadline=handoff.deadline();s.epochs={1,2,3,4};
    for(auto key:{AdmissionCondition::cpu_thread,AdmissionCondition::cpu_boundary,AdmissionCondition::paused,
        AdmissionCondition::pine_excluded,AdmissionCondition::vu_drained,AdmissionCondition::gs_drained})
      s.facts[static_cast<std::size_t>(key)]=AdmissionFact::satisfied;
    CHECK(ticket->publish(s));ready=true;
    while(!retire.load())std::this_thread::yield();
    CHECK(ticket->retire());
  }){
    eventually([&]{return ready.load();});
    worker=make_runtime_diagnostic_worker(expectation(),factory(work),handoff.binding());
    CHECK(worker);
  }
  std::shared_ptr<RuntimeDiagnosticTicket> queue_until(std::uint64_t id,Clock::time_point d) noexcept override {
    CHECK(id==1 && d==handoff.deadline());ticket=make_runtime_diagnostic_ticket(generation,clock);return ticket;
  }
  void release(){retire=true;if(cpu.joinable())cpu.join();}
  ~Runtime(){handoff.cancel();release();worker->cancel();worker->wait_stopped_until(Clock::now()+3s);}
};
struct Channel final : DiagnosticChannel {
  std::vector<std::uint8_t> input,output;
  std::size_t fragment{3};unsigned reads{},writes{},closes{};
  bool alive{true},close_ok{true},oversize{},read_ok{true},write_ok{true};
  Clock::duration wait{};
  std::function<void()> on_read,on_write,on_connected;
  void enqueue(std::uint64_t seq=1){const auto p=packet(seq);input.insert(input.end(),p.begin(),p.end());}
  bool connected() noexcept override {if(on_connected)on_connected();return alive;}
  bool read(std::uint8_t* bytes,std::size_t size,std::size_t& n,Clock::duration budget) noexcept override {
    ++reads;wait=budget;if(on_read)on_read();n=std::min({size,input.size(),fragment});
    std::copy_n(input.begin(),n,bytes);input.erase(input.begin(),input.begin()+n);
    if(oversize)n=size+1;
    return alive && read_ok;
  }
  bool write(const std::uint8_t* bytes,std::size_t size,std::size_t& n,Clock::duration) noexcept override {
    ++writes;if(on_write)on_write();n=std::min(size,fragment);output.insert(output.end(),bytes,bytes+n);return alive && write_ok;
  }
  bool close() noexcept override {++closes;alive=false;return close_ok;}
};
inline void complete(RuntimeDiagnosticSession& s){
  eventually([&]{auto r=s.step();CHECK(r!=Result::rejected);return r==Result::complete;});
}
inline void close(Runtime& r,RuntimeDiagnosticSession& s,Closed expected=Closed::closed){
  CHECK(s.close_until(Clock::now()+1ms)==Closed::pending);
  CHECK(!r.worker->status().joined);r.release();
  CHECK(s.close_until(Clock::now()+3s)==expected);
  CHECK(s.close_until(Clock::now())==expected && r.worker->status().joined);
}
} // namespace session_fixture
