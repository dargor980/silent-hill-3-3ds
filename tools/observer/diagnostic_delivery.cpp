#include "sh3_observer/diagnostic_delivery.hpp"
#include <algorithm>

namespace sh3::observer {
namespace {
DiagnosticDeliveryResult deliver(DiagnosticWorker& worker, DiagnosticDeliverySink& sink,
                                 const std::atomic<bool>* cancelled) noexcept {
  using Result = DiagnosticDeliveryResult;
  const auto checkpoint = [&] {
    if (cancelled && cancelled->load()) worker.cancel();
    return worker.delivery_checkpoint();
  };
  if (cancelled && cancelled->load()) { worker.cancel(); return Result::rejected; }
  DiagnosticCompletion result;
  if (!worker.take_for_delivery(result))
    return worker.status().reason == DiagnosticRejection::none ? Result::waiting : Result::rejected;
  std::size_t offset = 0;
  const DiagnosticClock::Clock::duration slice = std::chrono::milliseconds(20);
  while (offset < result.bytes.size()) {
    if (!checkpoint()) return Result::rejected;
    const auto remaining = worker.delivery_remaining();
    if (remaining <= DiagnosticClock::Clock::duration::zero()) return Result::rejected;
    std::size_t written = 0;
    const bool ok = sink.write(result.bytes.data()+offset, result.bytes.size()-offset,
                               written, std::min(slice, remaining));
    if (!checkpoint()) return Result::rejected;
    if (!ok || written > result.bytes.size()-offset) {
      worker.peer_lost(); return Result::rejected;
    }
    offset += written;
  }
  return worker.complete_delivery() ? Result::complete : Result::rejected;
}
}
DiagnosticDeliveryResult deliver_diagnostic(DiagnosticWorker& worker, DiagnosticDeliverySink& sink) noexcept {
  return deliver(worker,sink,nullptr);
}
DiagnosticDeliveryResult deliver_diagnostic(DiagnosticWorker& worker, DiagnosticDeliverySink& sink,
                                            const std::atomic<bool>& cancelled) noexcept {
  return deliver(worker,sink,&cancelled);
}
} // namespace sh3::observer
