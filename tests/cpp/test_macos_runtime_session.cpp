#include "runtime_session_fixture.hpp"
#include "sh3_observer/macos_diagnostic_sink.hpp"
#include "sh3_observer/macos_diagnostic_work.hpp"
#include "sh3_observer/macos_image_identity.hpp"
#include <mach-o/dyld.h>
#include <semaphore>
#include <string>
#include <unistd.h>
using namespace session_fixture;
int main(int argc,char** argv){
  CHECK(argc==2);const std::string mode=argv[1];
  int fd[2];CHECK(::socketpair(AF_UNIX,SOCK_STREAM,0,fd)==0);
  MacOSPeerIdentity peer;CHECK(read_macos_peer(fd[0],peer));
  if(mode=="identity")++peer.birth_ns;
  MacOSDiagnosticSink channel(fd[0],peer);Runtime runtime(system_diagnostic_clock());
  MacOSDiagnosticDetails detail;
  if(mode=="native_missing"){
    ImageSnapshot images;MacOSImageEvents events;CHECK(events.read(images));
    // Real native factory must reject a missing local manifest; no mock inventory.
    MacOSDiagnosticConfiguration config{"/nonexistent-sh3-session/manifest",expectation(),reinterpret_cast<std::uintptr_t>(_dyld_get_image_header(0))};
    runtime.worker=make_runtime_diagnostic_worker(expectation(),std::make_unique<MacOSDiagnosticWorkFactory>(config,nullptr,&detail),runtime.handoff.binding());
  }
  RuntimeDiagnosticSession session(runtime.handoff,*runtime.worker,channel);
  if(mode=="stable" || mode=="fragmented"){
    for(unsigned i=1;i<=3;++i){auto p=packet(i);
      if(mode=="fragmented"){
        CHECK(::send(fd[1],p.data(),9,0)==9);CHECK(session.step()==Result::waiting && runtime.work.samples==i-1);
        CHECK(::send(fd[1],p.data()+9,p.size()-9,0)==23);
      }else CHECK(::send(fd[1],p.data(),p.size(),0)==32);
      complete(session);DiagnosticBytes output{};
      CHECK(::recv(fd[1],output.data(),output.size(),MSG_WAITALL)==294);
      CHECK(output[8]==1 && output[32]==i && output[244]==1 && output[262]==1 && output[270]==2);
    }
  }else if(mode=="disconnect" || mode=="partial_eof" || mode=="identity"){
    if(mode=="partial_eof"){auto p=packet();CHECK(::send(fd[1],p.data(),9,0)==9);CHECK(session.step()==Result::waiting);}
    if(mode!="identity"){CHECK(::close(fd[1])==0);fd[1]=-1;}
    CHECK(session.step()==Result::rejected && session.failure()==Reason::peer_lost && runtime.work.creates==0);
  }else if(mode=="native_missing"){
    auto p=packet();CHECK(::send(fd[1],p.data(),p.size(),0)==32);
    eventually([&]{return session.step()==Result::rejected;});
    CHECK(session.failure()==Reason::configuration && runtime.work.creates==0);
  }else if(mode=="blocked_disconnect"){
    std::binary_semaphore entered(0),resume(0);runtime.work.sample_hook=[&](auto&){entered.release();resume.acquire();};
    auto p=packet();CHECK(::send(fd[1],p.data(),p.size(),0)==32);CHECK(session.step()==Result::waiting);entered.acquire();
    CHECK(::close(fd[1])==0);fd[1]=-1;CHECK(session.step()==Result::rejected && session.failure()==Reason::peer_lost);
    CHECK(session.close_until(Clock::now()+1ms)==Closed::pending && !runtime.worker->status().joined);
    runtime.release();CHECK(session.close_until(Clock::now()+1ms)==Closed::pending && runtime.work.closes==0);
    resume.release();CHECK(session.close_until(Clock::now()+3s)==Closed::closed);return 0;
  }else CHECK(false);
  close(runtime,session);CHECK(channel.close());
  if(mode=="native_missing")CHECK(!detail.prepared && detail.closed);
  if(fd[1]>=0)CHECK(::close(fd[1])==0);
}
