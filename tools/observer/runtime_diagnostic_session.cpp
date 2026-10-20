#include "sh3_observer/runtime_diagnostic_session.hpp"
#include <algorithm>

namespace sh3::observer {
namespace { using Reason = DiagnosticRejection; using Clock = DiagnosticClock::Clock; }
RuntimeDiagnosticSession::RuntimeDiagnosticSession(RuntimeDiagnosticHandoff& h,
    DiagnosticWorker& w, DiagnosticChannel& channel) noexcept
  : handoff_(h), worker_(w), channel_(channel), clock_(h.clock()), binding_(h.binding()),
    last_(clock_.now()), deadline_(h.deadline()) {
  if (h.failure()!=Reason::none) stop(h.failure());
  else if (!binding_ || !binding_->snapshot(snapshot_) || !w.bound_to(*binding_) ||
           snapshot_.deadline!=deadline_) stop(Reason::configuration);
  else check();
}
Reason RuntimeDiagnosticSession::stop(Reason reason) noexcept {
  if (reason_==Reason::none) reason_=reason;
  handoff_.cancel(reason_);
  worker_.cancel();
  return reason_;
}
bool RuntimeDiagnosticSession::check() noexcept {
  if (reason_!=Reason::none) return false;
  const auto runtime=handoff_.failure();
  if (runtime!=Reason::none) { stop(runtime); return false; }
  const auto now=clock_.now();
  if (now<last_) { stop(Reason::unavailable); return false; }
  last_=now;
  if (now>=deadline_) { stop(Reason::deadline); return false; }
  const auto worker=worker_.status().reason;
  if (worker!=Reason::none) { stop(worker); return false; }
  return true;
}
Reason RuntimeDiagnosticSession::failure() noexcept { check(); return reason_; }
void RuntimeDiagnosticSession::cancel() noexcept {
  check();
  stop(Reason::cancelled);
}
RuntimeSessionResult RuntimeDiagnosticSession::step() noexcept {
  return step_with_cancellation(nullptr);
}
RuntimeSessionResult RuntimeDiagnosticSession::step(const std::atomic<bool>& cancelled) noexcept {
  return step_with_cancellation(&cancelled);
}
RuntimeSessionResult RuntimeDiagnosticSession::step_with_cancellation(const std::atomic<bool>* cancelled) noexcept {
  constexpr auto rejected=RuntimeSessionResult::rejected;
  const auto checkpoint = [&] {
    if (cancelled && cancelled->load()) cancel();
    return check();
  };
  if (!checkpoint()) return rejected;
  if (!channel_.connected()) { stop(Reason::peer_lost); return rejected; }
  if (!checkpoint()) return rejected;
  if (!working_) {
    std::size_t count{};
    const auto remaining=deadline_-last_;
    const bool ok=channel_.read(packet_.data()+received_,packet_.size()-received_,count,
      std::min(remaining,Clock::duration(std::chrono::milliseconds(20))));
    if (!checkpoint()) return rejected;
    if (!ok) { stop(Reason::peer_lost); return rejected; }
    if (count>packet_.size()-received_) { stop(Reason::protocol); return rejected; }
    received_+=count;
    if (received_!=packet_.size()) return RuntimeSessionResult::waiting;
    DiagnosticRequest request;
    if (!decode_diagnostic_request(packet_.data(),packet_.size(),request)) {
      stop(Reason::protocol); return rejected;
    }
    if (!worker_.submit_until(request,snapshot_.epochs,deadline_)) {
      const auto reason=worker_.status().reason;
      stop(reason==Reason::none ? Reason::unavailable : reason); return rejected;
    }
    working_=true;
  }
  const auto result=cancelled ? deliver_diagnostic(worker_,channel_,*cancelled) :
                               deliver_diagnostic(worker_,channel_);
  if (!checkpoint()) return rejected;
  if (result==DiagnosticDeliveryResult::rejected) { stop(Reason::unavailable); return rejected; }
  if (result==DiagnosticDeliveryResult::waiting) return RuntimeSessionResult::waiting;
  received_=0;working_=false;
  // last_ is after delivery; idle time before the next step consumes this window.
  const auto left=handoff_.deadline()-last_;
  deadline_=last_+std::min(left,Clock::duration(std::chrono::seconds(2)));
  return RuntimeSessionResult::complete;
}
RuntimeSessionClose RuntimeDiagnosticSession::close_until(Clock::time_point deadline) {
  cancel();
  if (!channel_closed_) { channel_closed_=true; close_ok_=channel_.close(); }
  const bool clean=wait_runtime_diagnostic_stopped(handoff_,&worker_,deadline);
  if (!handoff_.quiescent() || !worker_.status().joined) return RuntimeSessionClose::pending;
  return clean && close_ok_ ? RuntimeSessionClose::closed : RuntimeSessionClose::failed;
}
} // namespace sh3::observer
