#include "runtime_service.hpp"
#include "runtime_frontend.hpp"
#include "sh3_observer/macos_diagnostic_sink.hpp"
#include "sh3_observer/macos_diagnostic_work.hpp"
#include "sh3_observer/macos_image_identity.hpp"
#include "sh3_observer/runtime_diagnostic_session.hpp"
#include <algorithm>
#include <cerrno>
#include <cstdio>
#include <cstdlib>
#include <cstring>
#include <fcntl.h>
#include <mach-o/dyld.h>
#include <optional>
#include <poll.h>
#include <sys/un.h>
#include <unistd.h>

namespace sh3::observer::pcsx2 {
namespace {
using Clock = DiagnosticClock::Clock;
using Reason = DiagnosticRejection;
using namespace std::chrono_literals;
struct Configuration {
  std::string endpoint;
  MacOSDiagnosticConfiguration work;
  std::uint32_t parent{}, euid{}, ruid{};
  std::uint64_t birth{};
  bool immediate{};
};
std::atomic<bool> cancelled{}, paused{}, finished{true};
std::thread io;
bool attempted{}; // UI only, exactly one session per process.
RuntimeUIIntent ui_intent; // UI only; released after cleanup and IO join.
bool hash(const char* text, Sha256& out) noexcept {
  out={};
  if (!text || std::strlen(text)!=64) return false;
  for (unsigned i=0;i<64;++i) {
    const auto c=text[i]; unsigned digit;
    if (c>='0' && c<='9') digit=c-'0';
    else if (c>='a' && c<='f') digit=c-'a'+10;
    else return false;
    out[i/2]|=static_cast<std::uint8_t>(digit<<(i%2 ? 0 : 4));
  }
  return true;
}
bool configure(Configuration& c) {
  const char* endpoint=std::getenv("SH3_RUNTIME_ENDPOINT");
  const char* manifest=std::getenv("SH3_RUNTIME_MANIFEST");
  const char* trigger=std::getenv("SH3_RUNTIME_TRIGGER");
  sockaddr_un address{};
  if (!endpoint || endpoint[0]!='/' || std::strlen(endpoint)>=sizeof(address.sun_path) ||
      !manifest || manifest[0]!='/' || !trigger ||
      (std::strcmp(trigger,"paused") && std::strcmp(trigger,"immediate"))) return false;
  c.endpoint=endpoint; c.work.manifest_path=manifest;
  c.work.expectation.profile=IdentityProfile::macos_platform_slices_v2;
  if (!hash(std::getenv("SH3_RUNTIME_POLICY"),c.work.expectation.policy_evidence) ||
      !hash(std::getenv("SH3_RUNTIME_MANIFEST_SHA256"),c.work.expectation.application_evidence) ||
      !hash(std::getenv("SH3_RUNTIME_PLATFORM"),c.work.expectation.platform_evidence)) return false;
  c.work.main_image=reinterpret_cast<std::uintptr_t>(_dyld_get_image_header(0));
  c.parent=static_cast<std::uint32_t>(::getppid());
  c.birth=read_macos_birth(static_cast<int>(c.parent));
  c.euid=::geteuid(); c.ruid=::getuid(); c.immediate=!std::strcmp(trigger,"immediate");
  return c.parent>1 && c.birth && c.work.main_image && valid_diagnostic_expectation(c.work.expectation);
}
bool active(Clock::time_point opened, Clock::time_point deadline) noexcept {
  const auto now=Clock::now();
  return !cancelled.load() && now>=opened && now<deadline;
}
// Raw descriptor is confined here until ownership passes to the channel.
int connect_parent(const Configuration& c, Clock::time_point opened,
                   Clock::time_point deadline, MacOSPeerIdentity& peer) noexcept {
  int fd=::socket(AF_UNIX,SOCK_STREAM,0);
  if (fd<0) return -1;
  const auto reject=[&]{::close(fd);return -1;};
  if (::fcntl(fd,F_SETFD,FD_CLOEXEC)<0 || ::fcntl(fd,F_SETFL,O_NONBLOCK)<0) return reject();
  sockaddr_un address{};address.sun_family=AF_UNIX;
  std::memcpy(address.sun_path,c.endpoint.c_str(),c.endpoint.size()+1);
  if (!active(opened,deadline)) return reject();
  const int result=::connect(fd,reinterpret_cast<sockaddr*>(&address),sizeof(address));
  if (result<0) {
    if (errno!=EINPROGRESS && errno!=EAGAIN) return reject();
    for (;;) {
      if (!active(opened,deadline)) return reject();
      pollfd p{fd,POLLOUT,0}; const int ready=::poll(&p,1,20);
      if (ready<0 && errno!=EINTR) return reject();
      if (ready<=0) continue;
      int error{};socklen_t size=sizeof(error);
      if (!(p.revents&POLLOUT) || ::getsockopt(fd,SOL_SOCKET,SO_ERROR,&error,&size)<0 || error) return reject();
      break;
    }
  }
  if (!active(opened,deadline) || !read_macos_peer(fd,peer) ||
      peer.pid!=c.parent || peer.birth_ns!=c.birth || peer.euid!=c.euid || peer.ruid!=c.ruid ||
      !active(opened,deadline)) return reject();
  return fd;
}
void run(Configuration c) noexcept {
  MacOSDiagnosticDetails detail;
  std::optional<MacOSDiagnosticSink> channel;
  std::shared_ptr<RuntimeDiagnosticHandoff> handoff;
  std::unique_ptr<DiagnosticWorker> worker;
  std::optional<RuntimeDiagnosticSession> session;
  Reason reason=Reason::none;
  unsigned replies{};
  bool clean=true, cpu_pending=false, dw_pending=false, release_waited=false;
  try {
    const auto waiting=Clock::now();
    while (!c.immediate && !paused.load() && active(waiting,waiting+60s))
      std::this_thread::sleep_for(1ms);
    if (cancelled.load()) reason=Reason::cancelled;
    else if (!c.immediate && !paused.load()) reason=Reason::deadline;
    if (reason==Reason::none) {
      const auto opened=Clock::now(), deadline=opened+5s;
      MacOSPeerIdentity peer;
      const int fd=connect_parent(c,opened,deadline,peer);
      if (fd<0) reason=cancelled.load() ? Reason::cancelled :
        Clock::now()>=deadline ? Reason::deadline : Reason::peer_lost;
      else {
        channel.emplace(fd,peer); // noexcept: ownership transfers exactly once.
        handoff=queue_runtime_diagnostic(deadline);
        if (!handoff) reason=Reason::unavailable;
        else {
          std::shared_ptr<RuntimeDiagnosticBinding> binding;
          while (handoff->failure()==Reason::none && !(binding=handoff->binding())) {
            if (cancelled.load()) handoff->cancel();
            else if (!channel->connected()) handoff->cancel(Reason::peer_lost);
            else std::this_thread::sleep_for(1ms);
          }
          reason=handoff->failure();
          if (reason==Reason::none && cancelled.load()) reason=Reason::cancelled;
          if (binding && reason==Reason::none && !cancelled.load()) {
            worker=make_runtime_diagnostic_worker(c.work.expectation,
              std::make_unique<MacOSDiagnosticWorkFactory>(c.work,nullptr,&detail),binding);
            if (!worker) reason=Reason::unavailable;
            else {
              session.emplace(*handoff,*worker,*channel);
              while (replies<3) {
                if (cancelled.load()) session->cancel();
                const auto result=session->step(cancelled);
                if (result==RuntimeSessionResult::rejected) break;
                if (result==RuntimeSessionResult::complete) ++replies;
                else std::this_thread::sleep_for(1ms);
              }
              reason=session->failure();
              if (reason==Reason::none && replies==3) {
                // The consumer validates peer identity and absence of EOF after
                // receiving the last frame, then releases its endpoint. Keep
                // CPU/DW and the owned channel alive within the original scope.
                release_waited=true;
                reason=channel->await_release(std::min(deadline,Clock::now()+2s),cancelled);
              }
            }
          }
        }
      }
    }
  } catch (...) { reason=Reason::unavailable; }
  // No stack-owned resource may unwind while a CPU scope or DW is still live.
  if (handoff) handoff->cancel(reason==Reason::none ? Reason::cancelled : reason);
  if (worker) worker->cancel();
  if (channel) clean=channel->close();
  if (handoff) {
    while (!handoff->quiescent()) { cpu_pending=true;std::this_thread::sleep_for(1ms); }
    if (worker) {
      while (!worker->status().joined) {
        const bool stopped=wait_runtime_diagnostic_stopped(*handoff,worker.get(),Clock::now()+20ms);
        if (worker->status().joined) clean=stopped && clean;
        else dw_pending=true;
      }
    }
  }
  // Telemetry is read only after DW has joined. It never grants capture.
  std::fprintf(stderr,"SH3_RT_END reason=%u replies=%u clean=%u cpu_pending=%u dw_pending=%u prepared=%u sampled=%u origins=%u inventory=%u release_waited=%u admitted=0\n",
    unsigned(reason),replies,unsigned(clean),unsigned(cpu_pending),unsigned(dw_pending),
    unsigned(detail.prepared),unsigned(detail.sampled),unsigned(detail.origins),unsigned(detail.inventory),unsigned(release_waited));
  std::fflush(stderr);
  // Publish only after every IO-owned resource is destroyed (outside this frame).
}
}
RuntimeServiceStart start_runtime_service() noexcept {
  if (attempted) return RuntimeServiceStart::failed;
  attempted=true;
  if (!std::getenv("SH3_RUNTIME_ENDPOINT")) return RuntimeServiceStart::disabled;
  try {
    Configuration configuration;
    if (!configure(configuration)) return RuntimeServiceStart::failed;
    ImageSnapshot initial;
    if (!MacOSImageEvents::read(initial)) return RuntimeServiceStart::failed;
    finished=false;
    io=std::thread([c=std::move(configuration)]() mutable { run(std::move(c));finished=true; });
    ui_intent.start();
    return RuntimeServiceStart::started;
  } catch (...) { finished=true;return RuntimeServiceStart::failed; }
}
void notify_runtime_service_paused() noexcept { paused=true; }
void cancel_runtime_service() noexcept { cancelled=true; }
bool cancel_runtime_service_from_ui() noexcept {
  if (!ui_intent.request_exit()) return false;
  cancel_runtime_service();
  return true;
}
bool defer_runtime_vm_shutdown(RuntimeVMShutdownRequest request) noexcept {
  if (!ui_intent.request_vm(request)) return false;
  cancel_runtime_service();
  return true;
}
RuntimeServiceUIAction poll_runtime_service_ui(RuntimeVMShutdownRequest& request) noexcept {
  request={};
  if (!ui_intent.active() || !finish_runtime_service()) return RuntimeServiceUIAction::none;
  return ui_intent.consume(request);
}
bool runtime_service_finished() noexcept { return finished.load(); }
bool finish_runtime_service() noexcept {
  if (!finished.load()) return false;
  if (io.joinable()) io.join();
  return true;
}
}
