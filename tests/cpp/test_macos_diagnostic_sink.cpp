#include "delivery_fixture.hpp"
#include "sh3_observer/macos_diagnostic_sink.hpp"
#include <algorithm>
#include <cerrno>
#include <fcntl.h>
#include <poll.h>
#include <string>
#include <sys/wait.h>
#include <unistd.h>
using namespace delivery_fixture;
namespace {
struct Pair {
  int fd[2]{-1,-1};MacOSPeerIdentity expected;
  Pair(){CHECK(::socketpair(AF_UNIX,SOCK_STREAM,0,fd)==0);CHECK(read_macos_peer(fd[0],expected));}
  int adopt(){int result=fd[0];fd[0]=-1;return result;}
  ~Pair(){for(auto n:fd)if(n>=0)::close(n);}
};
}
int main(int argc,char** argv){
  CHECK(argc==2);std::string mode=argv[1];DiagnosticBytes bytes{};bytes.fill(17);std::size_t n=99;
  if(mode=="release_delivery" || mode=="release_immediate_regression"){
    Pair p;MacOSDiagnosticSink sink(p.adopt(),p.expected);std::atomic<bool> cancelled{};
    CHECK(sink.write(bytes.data(),bytes.size(),n,20ms) && n==bytes.size());
    if(mode=="release_immediate_regression"){
      CHECK(sink.close());DiagnosticBytes received{};CHECK(::recv(p.fd[1],received.data(),received.size(),MSG_WAITALL)==294 && received==bytes);
      pollfd check{p.fd[1],POLLIN,0};CHECK(::poll(&check,1,0)==1);
      std::uint8_t extra{};CHECK(::recv(p.fd[1],&extra,1,MSG_PEEK)==0);
    }else{
      std::atomic<bool> validated{};
      std::thread consumer([&]{
        DiagnosticBytes received{};CHECK(::recv(p.fd[1],received.data(),received.size(),MSG_WAITALL)==294 && received==bytes);
        pollfd check{p.fd[1],POLLIN,0};CHECK(::poll(&check,1,0)==0);
        MacOSPeerIdentity identity;CHECK(read_macos_peer(p.fd[1],identity) && identity.pid==p.expected.pid);
        validated=true;CHECK(::shutdown(p.fd[1],SHUT_WR)==0);
      });
      CHECK(sink.await_release(Clock::now()+500ms,cancelled)==Reason::none);
      consumer.join();CHECK(validated && !sink.connected() && sink.close());
    }
  }else if(mode=="release_eof" || mode=="release_halfclose"){
    Pair p;MacOSDiagnosticSink sink(p.adopt(),p.expected);std::atomic<bool> cancelled{};
    CHECK(sink.connected());
    if(mode=="release_eof"){CHECK(::close(p.fd[1])==0);p.fd[1]=-1;}
    else CHECK(::shutdown(p.fd[1],SHUT_WR)==0);
    CHECK(sink.await_release(Clock::now()+500ms,cancelled)==
      (mode=="release_eof"?Reason::peer_lost:Reason::none));
    CHECK(!sink.connected() && sink.close());
  }else if(mode=="release_extra" || mode=="release_late_extra"){
    Pair p;MacOSDiagnosticSink sink(p.adopt(),p.expected);std::atomic<bool> cancelled{};
    std::thread sender([&]{if(mode=="release_late_extra")std::this_thread::sleep_for(20ms);CHECK(::send(p.fd[1],bytes.data(),1,0)==1);});
    CHECK(sink.await_release(Clock::now()+500ms,cancelled)==Reason::protocol);
    sender.join();CHECK(!sink.connected() && sink.close());
  }else if(mode=="release_cancelled" || mode=="release_cancel_during"){
    Pair p;MacOSDiagnosticSink sink(p.adopt(),p.expected);std::atomic<bool> cancelled{mode=="release_cancelled"};
    std::thread cancel([&]{if(mode=="release_cancel_during"){std::this_thread::sleep_for(20ms);cancelled=true;}});
    const auto opened=Clock::now();CHECK(sink.await_release(opened+500ms,cancelled)==Reason::cancelled);
    CHECK(Clock::now()-opened<250ms);cancel.join();CHECK(!sink.connected() && sink.close());
  }else if(mode=="release_deadline" || mode=="release_expired" || mode=="release_unbounded"){
    Pair p;MacOSDiagnosticSink sink(p.adopt(),p.expected);std::atomic<bool> cancelled{};
    const auto opened=Clock::now();const auto end=opened+(mode=="release_expired"?-1ms:mode=="release_unbounded"?3000ms:30ms);
    CHECK(sink.await_release(end,cancelled)==(mode=="release_unbounded"?Reason::configuration:Reason::deadline));
    CHECK(Clock::now()-opened<250ms);CHECK(!sink.connected() && sink.close());
  }else if(mode=="release_identity"){
    for(unsigned field=0;field<6;++field){Pair p;auto changed=p.expected;
      switch(field){case 0:++changed.pid;break;case 1:++changed.birth_ns;break;case 2:++changed.euid;break;
        case 3:++changed.ruid;break;case 4:++changed.pid_version;break;case 5:changed.token[0]^=1;break;}
      MacOSDiagnosticSink sink(p.adopt(),changed);std::atomic<bool> cancelled{};
      CHECK(sink.await_release(Clock::now()+500ms,cancelled)==Reason::peer_lost && sink.close());}
  }else if(mode=="release_foreign"){
    Pair p;MacOSDiagnosticSink sink(p.adopt(),p.expected);std::atomic<bool> cancelled{};
    std::thread other([&]{CHECK(sink.await_release(Clock::now()+500ms,cancelled)==Reason::peer_lost);});other.join();
    CHECK(!sink.connected() && sink.close());
  }else if(mode=="release_io_failure"){
    Pair p;const int fd=p.fd[0];MacOSDiagnosticSink sink(p.adopt(),p.expected);std::atomic<bool> cancelled{};
    CHECK(::close(fd)==0);CHECK(sink.await_release(Clock::now()+500ms,cancelled)==Reason::peer_lost);
    CHECK(!sink.close());
  }else if(mode=="read" || mode=="read_partial" || mode=="read_empty"){
    Pair p;MacOSDiagnosticSink sink(p.adopt(),p.expected);std::array<std::uint8_t,32> packet{},received{};packet.fill(23);
    CHECK(sink.connected());
    if(mode=="read_empty"){
      CHECK(sink.read(received.data(),received.size(),n,500us) && n==0 && sink.connected());
    }else{
      const auto first=mode=="read_partial"?7U:32U;
      CHECK(::send(p.fd[1],packet.data(),first,0)==first);
      CHECK(sink.connected() && sink.read(received.data(),received.size(),n,20ms) && n==first);
      if(first<32){CHECK(::send(p.fd[1],packet.data()+first,32-first,0)==32-first);CHECK(sink.read(received.data()+first,32-first,n,20ms) && n==32-first);}
      CHECK(received==packet);
    }
    CHECK(sink.close() && !sink.connected() && !sink.read(received.data(),32,n,20ms) && n==0);
  }else if(mode=="read_invalid"){
    for(unsigned which=0;which<5;++which){Pair p;MacOSDiagnosticSink sink(p.adopt(),p.expected);
      CHECK(!sink.read(which==0?nullptr:bytes.data(),which==1?0:which==2?33:32,n,which==3?0ms:which==4?21ms:20ms));
      CHECK(n==0 && !sink.connected() && sink.close());}
  }else if(mode=="read_identity"){
    for(unsigned field=0;field<6;++field){Pair p;auto changed=p.expected;
      switch(field){case 0:++changed.pid;break;case 1:++changed.birth_ns;break;case 2:++changed.euid;break;
        case 3:++changed.ruid;break;case 4:++changed.pid_version;break;case 5:changed.token[0]^=1;break;}
      MacOSDiagnosticSink sink(p.adopt(),changed);CHECK(!sink.read(bytes.data(),32,n,20ms) && n==0 && !sink.connected() && sink.close());}
  }else if(mode=="read_disconnect" || mode=="read_halfclose"){
    Pair p;MacOSDiagnosticSink sink(p.adopt(),p.expected);
    if(mode=="read_halfclose")CHECK(::shutdown(p.fd[1],SHUT_WR)==0);
    else{CHECK(::close(p.fd[1])==0);p.fd[1]=-1;}
    CHECK(!sink.read(bytes.data(),32,n,20ms) && n==0 && !sink.connected() && sink.close());
  }else if(mode=="read_foreign"){
    Pair p;MacOSDiagnosticSink sink(p.adopt(),p.expected);std::thread other([&]{CHECK(!sink.read(bytes.data(),32,n,20ms) && n==0);});other.join();
    CHECK(!sink.connected() && sink.close());
  }else if(mode=="stable"){
    Pair p;MacOSDiagnosticSink sink(p.adopt(),p.expected);
    CHECK(sink.write(bytes.data(),bytes.size(),n,20ms) && n==bytes.size());
    DiagnosticBytes received{};CHECK(::recv(p.fd[1],received.data(),received.size(),0)==294 && received==bytes);
    CHECK(sink.close() && sink.close());CHECK(!sink.write(bytes.data(),bytes.size(),n,20ms) && n==0);
  }else if(mode=="delivery"){
    Pair p;MacOSDiagnosticSink sink(p.adopt(),p.expected);State s;DiagnosticWorker w(expectation(),factory(s));
    CHECK(w.submit_until(request(),{},Clock::now()+5s));DiagnosticDeliveryResult result;
    eventually([&]{result=deliver_diagnostic(w,sink);return result!=DiagnosticDeliveryResult::waiting;});
    CHECK(result==DiagnosticDeliveryResult::complete);DiagnosticBytes received{};
    CHECK(::recv(p.fd[1],received.data(),received.size(),0)==294 && received[8]==1 && received[9]==2);
    w.cancel();stopped(w,Reason::cancelled);CHECK(sink.close());
  }else if(mode=="backpressure"){
    Pair p;const int one=4096;CHECK(::setsockopt(p.fd[0],SOL_SOCKET,SO_SNDBUF,&one,sizeof(one))==0);
    CHECK(::fcntl(p.fd[0],F_SETFL,O_NONBLOCK)==0);std::array<char,4096> fill{};
    while(::send(p.fd[0],fill.data(),fill.size(),0)>0){}CHECK(errno==EAGAIN || errno==EWOULDBLOCK);
    MacOSDiagnosticSink sink(p.adopt(),p.expected);
    CHECK(sink.write(bytes.data(),bytes.size(),n,20ms) && n==0);
    CHECK(::fcntl(p.fd[1],F_SETFL,O_NONBLOCK)==0);
    while(::recv(p.fd[1],fill.data(),fill.size(),0)>0){}
    CHECK(sink.write(bytes.data(),bytes.size(),n,500us) && n==294);CHECK(sink.close());
  }else if(mode=="invalid"){
    for(unsigned which=0;which<5;++which){
      Pair p;MacOSDiagnosticSink sink(p.adopt(),p.expected);
      CHECK(!sink.write(which==0?nullptr:bytes.data(),which==1?0:which==2?295:294,n,which==3?0ms:which==4?21ms:20ms));
      CHECK(n==0 && !sink.write(bytes.data(),294,n,20ms));CHECK(sink.close());
    }
    MacOSDiagnosticSink invalid(-1,{});CHECK(!invalid.write(bytes.data(),294,n,20ms));CHECK(invalid.close());
  }else if(mode=="identity"){
    for(unsigned field=0;field<6;++field){
      Pair p;auto changed=p.expected;
      switch(field){case 0:++changed.pid;break;case 1:++changed.birth_ns;break;case 2:++changed.euid;break;
        case 3:++changed.ruid;break;case 4:++changed.pid_version;break;case 5:changed.token[0]^=1;break;}
      MacOSDiagnosticSink sink(p.adopt(),changed);CHECK(!sink.write(bytes.data(),294,n,20ms) && n==0);CHECK(sink.close());
    }
  }else if(mode=="disconnect"){
    Pair p;MacOSDiagnosticSink sink(p.adopt(),p.expected);CHECK(::close(p.fd[1])==0);p.fd[1]=-1;
    CHECK(!sink.write(bytes.data(),294,n,20ms) && n==0);CHECK(sink.close());
  }else if(mode=="foreign"){
    for(bool close:{false,true}){
      Pair p;const int fd=p.fd[0];MacOSDiagnosticSink sink(p.adopt(),p.expected);bool result=true;
      std::thread t([&]{result=close?sink.close():sink.write(bytes.data(),294,n,20ms);});t.join();
      CHECK(!result && ::fcntl(fd,F_GETFD)>=0);CHECK(!sink.write(bytes.data(),294,n,20ms));CHECK(sink.close());
    }
  }else if(mode=="close_error"){
    Pair p;int fd=p.fd[0];MacOSDiagnosticSink sink(p.adopt(),p.expected);
    CHECK(::close(fd)==0);CHECK(!sink.close() && !sink.close());
  }else if(mode=="fork"){
    Pair p;MacOSDiagnosticSink sink(p.adopt(),p.expected);const auto pid=::fork();CHECK(pid>=0);
    if(pid==0){CHECK(!sink.write(bytes.data(),294,n,20ms));CHECK(sink.close());::_exit(0);}
    int status{};CHECK(::waitpid(pid,&status,0)==pid && WIFEXITED(status) && WEXITSTATUS(status)==0);
    CHECK(sink.write(bytes.data(),294,n,20ms) && n==294);CHECK(sink.close());
  }else CHECK(false);
}
