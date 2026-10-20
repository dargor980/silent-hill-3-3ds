#include "sh3_observer/diagnostic_worker.hpp"
#include <algorithm>
#include <condition_variable>
#include <mutex>
#include <thread>

namespace sh3::observer {
namespace {
using Clock = DiagnosticClock::Clock;
using Reason = DiagnosticRejection;
using Phase = DiagnosticWorkerPhase;
class SystemClock final : public DiagnosticClock {
  Clock::time_point now() noexcept override { return Clock::now(); }
};
bool same_epochs(const DiagnosticEpochs& a, const DiagnosticEpochs& b) noexcept {
  return a.host == b.host && a.pine == b.pine && a.vu == b.vu && a.gs == b.gs;
}
bool valid_epochs(const DiagnosticEpochs& e) noexcept {
  const auto valid = [](auto n) { return n && n != UINT64_MAX; };
  return same_epochs(e, {}) || (valid(e.host) && valid(e.pine) && valid(e.vu) && valid(e.gs));
}
}
DiagnosticClock& system_diagnostic_clock() noexcept {
  static SystemClock clock;
  return clock;
}
struct DiagnosticWorkerState final {
  const DiagnosticExpectation expectation;
  std::unique_ptr<DiagnosticWorkFactory> factory;
  DiagnosticClock& clock;
  const std::shared_ptr<const DiagnosticValidity> validity;
  std::mutex mutex;
  std::condition_variable wake;
  std::thread thread;
  Reason reason{Reason::none};
  Phase phase{Phase::idle};
  bool started{}, pending{}, ready{}, finished{}, cleanup_verified{}, joined{};
  bool retained_delivery{}, delivering{};
  bool have_clock{}, have_baseline{};
  Clock::time_point deadline{}, last_time{};
  DiagnosticRequest request{};
  DiagnosticEpochs epochs{};
  DiagnosticCompletion completion{};
  DiagnosticBytes baseline{};
  std::uint64_t delivered{};

  DiagnosticWorkerState(DiagnosticExpectation e, std::unique_ptr<DiagnosticWorkFactory> f,
                        DiagnosticClock& c, std::shared_ptr<const DiagnosticValidity> v)
    : expectation(e), factory(std::move(f)), clock(c), validity(std::move(v)) {
    if (!factory || !valid_diagnostic_expectation(expectation)) stop(Reason::configuration);
  }
  // All methods except run use the mutex. No adapter calls under this lock.
  void stop(Reason why) noexcept {
    if (reason == Reason::none) reason = why;
    completion = {}; baseline = {}; ready = delivering = false;
    if (!started) { finished = cleanup_verified = true; phase = Phase::stopped; }
    wake.notify_all();
  }
  bool check() noexcept {
    if (reason != Reason::none) return false;
    if (validity) {
      const auto value = validity->failure();
      if (value != Reason::none) {
        stop(value >= Reason::configuration && value <= Reason::unavailable ? value : Reason::protocol);
        return false;
      }
    }
    if (!pending) return true;
    const auto now = clock.now();
    if (have_clock && now < last_time) { stop(Reason::unavailable); return false; }
    last_time = now; have_clock = true;
    if (now >= deadline) { stop(Reason::deadline); return false; }
    return true;
  }
  bool step(Phase next) noexcept {
    std::lock_guard lock(mutex);
    if (!check()) return false;
    phase = next;
    return true;
  }
  bool returned(Reason value) noexcept {
    std::lock_guard lock(mutex);
    if (!check()) return false;
    if (value == Reason::none) return true;
    stop(value >= Reason::configuration && value <= Reason::unavailable ? value : Reason::protocol);
    return false;
  }
  void run() noexcept {
    std::unique_ptr<DiagnosticWork> work;
    DiagnosticBudget budget(*this);
    try {
      if (step(Phase::preparing)) work = factory->create(budget);
      factory.reset();
      if (!work) returned(Reason::unavailable);
      if (work && budget.checkpoint() && returned(work->prepare(budget))) {
        for (;;) {
          {
            std::unique_lock lock(mutex);
            if (validity) {
              while (!pending && check()) wake.wait_for(lock, std::chrono::milliseconds(20));
            } else {
              wake.wait(lock, [&] { return pending || reason != Reason::none; });
            }
            if (!check()) break;
          }
          if (!step(Phase::sampling)) break;
          DiagnosticObservation observation;
          if (!returned(work->sample(budget, observation))) break;
          DiagnosticCompletion result;
          // request/epochs cannot change while pending; submit rejects overlap.
          if (!encode_platform_diagnostic(expectation, request, observation.inventory,
                                          observation.facts, observation.epochs, result.bytes)) {
            returned(Reason::protocol); break;
          }
          result.gates = assess_profile(observation.facts);
          std::unique_lock lock(mutex);
          if (!check()) break;
          if (!same_epochs(observation.epochs, epochs)) { stop(Reason::lifecycle); break; }
          // Canonical PD identity bytes; correlation/facts may change, identity cannot.
          if (have_baseline && !std::equal(result.bytes.begin()+40, result.bytes.begin()+244,
                                            baseline.begin()+40)) {
            stop(Reason::identity_changed); break;
          }
          baseline = result.bytes; have_baseline = true;
          completion = result; ready = true; phase = Phase::ready;
          wake.notify_all();
          // Retained delivery keeps pending after extraction, until confirmation.
          while ((ready || delivering) && check()) {
            const auto remaining = deadline-last_time;
            const Clock::duration slice = std::chrono::milliseconds(20);
            wake.wait_for(lock, validity ? std::min(remaining, slice) : remaining);
          }
          if (!check()) break;
        }
      }
    } catch (...) {
      returned(Reason::unavailable);
    }
    {
      std::lock_guard lock(mutex);
      phase = Phase::closing;
    }
    const bool closed = !work || work->close();
    work.reset();
    factory.reset();
    {
      std::lock_guard lock(mutex);
      cleanup_verified = closed; finished = true; phase = Phase::stopped;
      wake.notify_all();
    }
  }
};
bool DiagnosticBudget::checkpoint() noexcept {
  std::lock_guard lock(state_.mutex);
  return state_.check();
}
Clock::duration DiagnosticBudget::remaining() noexcept {
  std::lock_guard lock(state_.mutex);
  return state_.check() ? state_.deadline-state_.last_time : Clock::duration::zero();
}
DiagnosticWorker::DiagnosticWorker(DiagnosticExpectation e, std::unique_ptr<DiagnosticWorkFactory> f,
                                   DiagnosticClock& clock, std::shared_ptr<const DiagnosticValidity> validity)
  : state_(std::make_unique<DiagnosticWorkerState>(e, std::move(f), clock, std::move(validity))) {}
bool DiagnosticWorker::bound_to(const DiagnosticValidity& binding) const noexcept {
  return state_->validity.get() == &binding;
}
DiagnosticWorker::~DiagnosticWorker() {
  cancel();
  if (state_->thread.joinable()) state_->thread.join();
}
bool DiagnosticWorker::submit(const DiagnosticRequest& request, const DiagnosticEpochs& epochs) noexcept {
  return submit_impl(request, epochs, nullptr);
}
bool DiagnosticWorker::submit_until(const DiagnosticRequest& request, const DiagnosticEpochs& epochs,
                                    Clock::time_point deadline) noexcept {
  return submit_impl(request, epochs, &deadline);
}
bool DiagnosticWorker::submit_impl(const DiagnosticRequest& request, const DiagnosticEpochs& epochs,
                                   const Clock::time_point* external) noexcept {
  auto& s = *state_;
  std::lock_guard lock(s.mutex);
  if (!s.check()) return false;
  const auto now = s.clock.now(); // Before validation, thread creation and preparation.
  const auto duration = std::chrono::seconds(s.started ? 2 : 5);
  DiagnosticBytes validation;
  if (s.pending || (s.started && s.retained_delivery != (external != nullptr)) ||
      !encode_diagnostic_rejection(request, Reason::cancelled, validation) ||
      request.sequence != s.delivered+1 || (s.started && request.challenge != s.request.challenge)) {
    s.stop(Reason::protocol); return false;
  }
  if (!valid_epochs(epochs) || (s.started && !same_epochs(epochs, s.epochs))) {
    s.stop(Reason::lifecycle); return false;
  }
  if ((s.have_clock && now < s.last_time) || now > Clock::time_point::max()-duration) {
    s.stop(Reason::unavailable); return false;
  }
  s.last_time = now; s.have_clock = true;
  s.deadline = external ? std::min(*external, now+duration) : now+duration;
  if (s.deadline <= now) { s.stop(Reason::deadline); return false; }
  s.retained_delivery = external != nullptr;
  s.request = request; s.epochs = epochs; s.pending = true; s.phase = Phase::queued;
  if (!s.started) {
    try {
      s.started = true;
      s.thread = std::thread([&s] { s.run(); });
    } catch (...) {
      s.started = false; s.stop(Reason::unavailable); return false;
    }
  }
  s.wake.notify_all();
  return true;
}
bool DiagnosticWorker::take(DiagnosticCompletion& out) noexcept {
  out = {};
  auto& s = *state_;
  std::lock_guard lock(s.mutex);
  if (!s.check()) return false;
  if (s.started && s.retained_delivery) { s.stop(Reason::protocol); return false; }
  if (!s.ready) return false;
  out = s.completion; s.completion = {}; s.ready = s.pending = false;
  s.delivered = s.request.sequence; s.phase = Phase::idle;
  s.wake.notify_all();
  return true;
}
bool DiagnosticWorker::take_for_delivery(DiagnosticCompletion& out) noexcept {
  out = {};
  auto& s = *state_;
  std::lock_guard lock(s.mutex);
  if (!s.check()) return false;
  if (s.delivering || (s.started && !s.retained_delivery)) {
    s.stop(Reason::protocol); return false;
  }
  if (!s.ready) return false;
  out = s.completion; s.completion = {}; s.ready = false;
  s.delivering = true; s.phase = Phase::delivering;
  s.wake.notify_all();
  return true;
}
bool DiagnosticWorker::delivery_checkpoint() noexcept {
  std::lock_guard lock(state_->mutex);
  return state_->check() && state_->delivering;
}
Clock::duration DiagnosticWorker::delivery_remaining() noexcept {
  std::lock_guard lock(state_->mutex);
  return state_->check() && state_->delivering ? state_->deadline-state_->last_time : Clock::duration::zero();
}
bool DiagnosticWorker::complete_delivery() noexcept {
  auto& s = *state_;
  std::lock_guard lock(s.mutex);
  if (!s.check()) return false;
  if (!s.delivering) { s.stop(Reason::protocol); return false; }
  s.delivering = s.pending = false; s.delivered = s.request.sequence; s.phase = Phase::idle;
  s.wake.notify_all();
  return true;
}
void DiagnosticWorker::cancel() noexcept {
  std::lock_guard lock(state_->mutex);
  state_->check(); state_->stop(Reason::cancelled);
}
void DiagnosticWorker::peer_lost() noexcept {
  std::lock_guard lock(state_->mutex);
  state_->check(); state_->stop(Reason::peer_lost);
}
void DiagnosticWorker::lifecycle(const DiagnosticEpochs& epochs) noexcept {
  std::lock_guard lock(state_->mutex);
  if (!state_->check()) return;
  if (!valid_epochs(epochs) || (state_->started && !same_epochs(epochs, state_->epochs)))
    state_->stop(Reason::lifecycle);
}
DiagnosticWorkerStatus DiagnosticWorker::status() noexcept {
  std::lock_guard lock(state_->mutex);
  state_->check();
  return {state_->reason, state_->phase, state_->cleanup_verified, state_->joined};
}
bool DiagnosticWorker::wait_stopped_until(Clock::time_point deadline) {
  auto& s = *state_;
  {
    std::unique_lock lock(s.mutex);
    if (!s.wake.wait_until(lock, deadline, [&] { return s.finished; })) return false;
  }
  if (s.thread.joinable()) s.thread.join();
  std::lock_guard lock(s.mutex);
  s.joined = true;
  return s.cleanup_verified;
}
} // namespace sh3::observer
