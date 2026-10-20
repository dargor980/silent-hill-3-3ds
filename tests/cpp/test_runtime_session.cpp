#include "runtime_session_fixture.hpp"
#include <semaphore>
#include <string>
using namespace session_fixture;
int main(int argc,char** argv){
  CHECK(argc==2);const std::string mode=argv[1];FakeClock clock;Runtime runtime(clock);Channel channel;
  if(mode=="unbound" || mode=="wrong_binding"){
    auto other=std::make_shared<RuntimeDiagnosticBinding>(clock);
    DiagnosticWorker wrong(expectation(),factory(runtime.work),clock,mode=="unbound"?nullptr:other);
    RuntimeDiagnosticSession session(runtime.handoff,wrong,channel);
    CHECK(session.failure()==Reason::configuration && session.step()==Result::rejected && channel.reads==0);
    runtime.release();CHECK(session.close_until(Clock::now()+3s)==Closed::closed);return 0;
  }
  RuntimeDiagnosticSession session(runtime.handoff,*runtime.worker,channel);
  CHECK(session.failure()==Reason::none);
  Closed expected=Closed::closed;
  if(mode=="stable"){
    for(unsigned i=1;i<=3;++i){channel.enqueue(i);complete(session);CHECK(channel.output.size()==i*294 && runtime.work.samples==i);}
    CHECK(runtime.work.creates==1 && runtime.work.prepares==1 && channel.reads==33);
    CHECK(channel.output[244]==1 && channel.output[245]==1); // CPU and boundary facts.
    for(unsigned i=0;i<4;++i)CHECK(channel.output[262+8*i]==i+1);
  }else if(mode=="external_cancel"){
    // Exercise each cancellation boundary using fresh CPU/DW owners.
    for(unsigned where=0;where<6;++where){
      FakeClock c;Runtime r(c);Channel ch;RuntimeDiagnosticSession s(r.handoff,*r.worker,ch);
      std::atomic<bool> signal{where==0};ch.enqueue();
      if(where==1)ch.on_connected=[&]{signal=true;};
      if(where==2)ch.on_read=[&]{signal=true;};
      if(where==3)ch.on_write=[&]{signal=true;};
      if(where==4){s.cancel();signal=true;c.add(5s);}
      if(where==5){r.handoff.cancel(Reason::peer_lost);signal=true;}
      eventually([&]{return s.step(signal)==Result::rejected;});
      CHECK(s.failure()==(where==5?Reason::peer_lost:Reason::cancelled));
      CHECK(ch.writes==(where==3?1U:0U) && ch.output.size()==(where==3?3U:0U));
      CHECK(s.step(signal)==Result::rejected);close(r,s);CHECK(ch.closes==1);
    }
  }else if(mode=="receive_cost"){
    clock.add(4s);channel.on_read=[&]{clock.add(1s);};channel.enqueue();
    CHECK(session.step()==Result::rejected && session.failure()==Reason::deadline && runtime.work.creates==0);
  }else if(mode=="queue_cost"){
    clock.add(5s);CHECK(session.step()==Result::rejected && channel.reads==0 && session.failure()==Reason::deadline);
  }else if(mode=="window" || mode=="scope"){
    if(mode=="scope")clock.add(4s);
    channel.enqueue();complete(session);clock.add(mode=="scope"?1s:2s);
    CHECK(session.step()==Result::rejected && session.failure()==Reason::deadline && runtime.work.samples==1);
  }else if(mode=="remaining"){
    clock.add(5s-500us);CHECK(session.step()==Result::waiting && channel.wait==500us);
  }else if(mode=="partial"){
    auto p=packet();channel.input.insert(channel.input.end(),p.begin(),p.begin()+9);
    for(unsigned i=0;i<4;++i)CHECK(session.step()==Result::waiting);
    CHECK(runtime.work.creates==0);channel.input.insert(channel.input.end(),p.begin()+9,p.end());complete(session);
  }else if(mode=="malformed" || mode=="sequence" || mode=="challenge"){
    if(mode=="challenge"){channel.enqueue();complete(session);channel.enqueue(2);channel.input[8]^=1;}
    else {channel.enqueue(mode=="sequence"?2:1);if(mode=="malformed")channel.input[0]^=1;}
    eventually([&]{return session.step()==Result::rejected;});CHECK(session.failure()==Reason::protocol);
    CHECK(runtime.work.samples==(mode=="challenge"?1U:0U));
  }else if(mode=="oversize"){
    channel.oversize=true;CHECK(session.step()==Result::rejected && session.failure()==Reason::protocol);
  }else if(mode=="read_failure" || mode=="disconnect"){
    if(mode=="read_failure")channel.read_ok=false;else channel.alive=false;
    CHECK(session.step()==Result::rejected && session.failure()==Reason::peer_lost && runtime.work.creates==0);
  }else if(mode=="write_failure" || mode=="write_deadline" || mode=="write_revoke"){
    channel.enqueue();
    if(mode=="write_failure")channel.write_ok=false;
    if(mode=="write_deadline")channel.on_write=[&]{clock.add(5s);};
    if(mode=="write_revoke")channel.on_write=[&]{runtime.generation.advance();};
    eventually([&]{return session.step()==Result::rejected;});CHECK(channel.writes==1);
    CHECK(session.failure()==(mode=="write_failure"?Reason::peer_lost:mode=="write_deadline"?Reason::deadline:Reason::lifecycle));
  }else if(mode=="rollback"){
    clock.add(1s);CHECK(session.step()==Result::waiting);clock.add(-1ns);
    CHECK(session.step()==Result::rejected && session.failure()==Reason::unavailable);
  }else if(mode=="check_cost"){
    channel.on_connected=[&]{clock.add(5s);};CHECK(session.step()==Result::rejected && channel.reads==0);
  }else if(mode=="lifecycle"){
    runtime.generation.advance();CHECK(session.step()==Result::rejected && session.failure()==Reason::lifecycle && channel.reads==0);
  }else if(mode=="cancel"){
    session.cancel();clock.add(5s);runtime.generation.advance();CHECK(session.failure()==Reason::cancelled && session.step()==Result::rejected);
  }else if(mode=="blocked" || mode=="disconnect_work"){
    std::binary_semaphore entered(0),resume(0);
    runtime.work.sample_hook=[&](auto&){entered.release();resume.acquire();};channel.enqueue();
    for(unsigned i=0;i<11;++i)CHECK(session.step()==Result::waiting);
    entered.acquire();if(mode=="disconnect_work"){channel.alive=false;CHECK(session.step()==Result::rejected && session.failure()==Reason::peer_lost);}
    CHECK(session.close_until(Clock::now()+1ms)==Closed::pending && !runtime.worker->status().joined);
    runtime.release();CHECK(session.close_until(Clock::now()+1ms)==Closed::pending && runtime.work.closes==0);
    resume.release();CHECK(session.close_until(Clock::now()+3s)==Closed::closed && runtime.work.closes==1);
    CHECK(channel.closes==1);return 0;
  }else if(mode=="channel_close" || mode=="worker_close"){
    channel.enqueue();complete(session);expected=Closed::failed;
    if(mode=="channel_close")channel.close_ok=false;else runtime.work.close_ok=false;
  }else if(mode=="destructor"){
    {RuntimeDiagnosticSession temporary(runtime.handoff,*runtime.worker,channel);}
    CHECK(session.failure()==Reason::cancelled && !runtime.worker->status().joined && channel.closes==0);
  }else CHECK(false);
  close(runtime,session,expected);CHECK(channel.closes==1 && session.step()==Result::rejected);
}
