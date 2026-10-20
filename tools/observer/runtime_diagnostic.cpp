#include "sh3_observer/runtime_diagnostic.hpp"
#include <utility>

namespace sh3::observer {
namespace {
using Reason = DiagnosticRejection;
using Clock = DiagnosticClock::Clock;
static_assert(std::atomic<Reason>::is_always_lock_free);
static_assert(std::atomic<bool>::is_always_lock_free);
bool epochs_equal(const DiagnosticEpochs& a, const DiagnosticEpochs& b) noexcept {
  return a.host==b.host && a.pine==b.pine && a.vu==b.vu && a.gs==b.gs;
}
bool normalize(RuntimeDiagnosticSnapshot& value) noexcept {
  const auto valid=[](auto n){return n && n!=UINT64_MAX;};
  if(!valid(value.scope_id) || !valid(value.epochs.host) || !valid(value.epochs.pine) ||
     !valid(value.epochs.vu) || !valid(value.epochs.gs)) return false;
  for(auto& fact:value.facts)
    if(fact!=AdmissionFact::satisfied && fact!=AdmissionFact::violated) fact=AdmissionFact::unknown;
  for(const auto key:{AdmissionCondition::cpu_thread,AdmissionCondition::cpu_boundary,
      AdmissionCondition::paused,AdmissionCondition::pine_excluded,AdmissionCondition::gs_drained,
      AdmissionCondition::vu_drained})
    if(value.facts[static_cast<std::size_t>(key)]!=AdmissionFact::satisfied) return false;
  return true;
}
class RuntimeWork final : public DiagnosticWork {
public:
  explicit RuntimeWork(std::shared_ptr<RuntimeDiagnosticBinding> binding) noexcept
    : binding_(std::move(binding)) {}
  bool create(DiagnosticWorkFactory& factory, DiagnosticBudget& budget) {
    child_=factory.create(budget); return bool(child_);
  }
  Reason prepare(DiagnosticBudget& budget) override {
    if(!budget.checkpoint()) return Reason::unavailable;
    const auto result=child_->prepare(budget);
    return budget.checkpoint() ? result : Reason::unavailable;
  }
  Reason sample(DiagnosticBudget& budget, DiagnosticObservation& out) override {
    out={}; RuntimeDiagnosticSnapshot runtime;
    if(!budget.checkpoint() || !binding_->snapshot(runtime)) return Reason::lifecycle;
    DiagnosticObservation value;
    const auto result=child_->sample(budget,value);
    if(!budget.checkpoint() || binding_->failure()!=Reason::none) return Reason::lifecycle;
    if(result!=Reason::none) return result;
    if(!epochs_equal(value.epochs,{}) || value.facts!=AdmissionProfile{}) return Reason::protocol;
    value.epochs=runtime.epochs; value.facts=runtime.facts;
    out=value; return Reason::none;
  }
  bool close() noexcept override { return child_->close(); }
private:
  std::unique_ptr<DiagnosticWork> child_;
  const std::shared_ptr<RuntimeDiagnosticBinding> binding_;
};
class RuntimeDiagnosticWorkFactory final : public DiagnosticWorkFactory {
public:
  RuntimeDiagnosticWorkFactory(std::unique_ptr<DiagnosticWorkFactory> child,
      std::shared_ptr<RuntimeDiagnosticBinding> binding) noexcept
    : child_(std::move(child)), binding_(std::move(binding)) {}
  std::unique_ptr<DiagnosticWork> create(DiagnosticBudget& budget) override {
    if(binding_->failure()!=Reason::none || !budget.checkpoint()) return {};
    // Allocate the decorator before the child can acquire resources.
    auto work=std::make_unique<RuntimeWork>(binding_);
    if(!work->create(*child_,budget)) return {};
    return work;
  }
private:
  const std::unique_ptr<DiagnosticWorkFactory> child_;
  const std::shared_ptr<RuntimeDiagnosticBinding> binding_;
};
}
RuntimeDiagnosticBinding::RuntimeDiagnosticBinding(DiagnosticClock& clock,
    const RuntimeRevocation* revocation) noexcept
  : clock_(clock), revocation_(revocation), revision_(revocation ? revocation->current() : 0),
    owner_(std::this_thread::get_id()) {}
Reason RuntimeDiagnosticBinding::stop(Reason reason) const noexcept {
  if(reason<Reason::configuration || reason>Reason::unavailable) reason=Reason::protocol;
  auto expected=Reason::none;
  reason_.compare_exchange_strong(expected,reason);
  return reason_.load();
}
void RuntimeDiagnosticBinding::revoke(Reason reason) noexcept { stop(reason); }
bool RuntimeDiagnosticBinding::activate(RuntimeDiagnosticSnapshot value) noexcept {
  if(std::this_thread::get_id()!=owner_) { stop(Reason::lifecycle); return false; }
  if(attempted_) { stop(Reason::protocol); return false; }
  attempted_=true;
  if(reason_.load()!=Reason::none) return false;
  if(revocation_ && (!revision_ || revision_==UINT64_MAX || revocation_->current()!=revision_)) {
    stop(Reason::lifecycle); return false;
  }
  if(!normalize(value)) { stop(Reason::lifecycle); return false; }
  const auto now=clock_.now();
  if(value.deadline<=now) { stop(Reason::deadline); return false; }
  if(now>Clock::time_point::max()-std::chrono::seconds(5) || value.deadline>now+std::chrono::seconds(5)) {
    stop(Reason::configuration); return false;
  }
  value_=value; opened_=now;
  ready_.store(true,std::memory_order_release);
  return failure()==Reason::none;
}
Reason RuntimeDiagnosticBinding::failure() const noexcept {
  const auto reason=reason_.load();
  if(reason!=Reason::none) return reason;
  if(revocation_ && (!revision_ || revision_==UINT64_MAX || revocation_->current()!=revision_))
    return stop(Reason::lifecycle);
  if(!ready_.load(std::memory_order_acquire)) return Reason::unavailable;
  const auto now=clock_.now();
  if(now<opened_) return stop(Reason::unavailable);
  if(now>=value_.deadline) return stop(Reason::deadline);
  return reason_.load();
}
bool RuntimeDiagnosticBinding::snapshot(RuntimeDiagnosticSnapshot& out) const noexcept {
  out={};
  if(failure()!=Reason::none) return false;
  out=value_;
  if(failure()!=Reason::none) { out={}; return false; }
  return true;
}
bool RuntimeDiagnosticBinding::revalidate(RuntimeDiagnosticSnapshot value) noexcept {
  if(std::this_thread::get_id()!=owner_) { stop(Reason::lifecycle); return false; }
  if(failure()!=Reason::none) return false;
  if(!normalize(value) || value.scope_id!=value_.scope_id || value.deadline!=value_.deadline ||
     !epochs_equal(value.epochs,value_.epochs) || value.facts!=value_.facts) {
    stop(Reason::lifecycle); return false;
  }
  return failure()==Reason::none;
}
std::unique_ptr<DiagnosticWorker> make_runtime_diagnostic_worker(DiagnosticExpectation expectation,
    std::unique_ptr<DiagnosticWorkFactory> child, std::shared_ptr<RuntimeDiagnosticBinding> binding) {
  if(!binding || !child) return {};
  auto factory=std::make_unique<RuntimeDiagnosticWorkFactory>(std::move(child),binding);
  return std::make_unique<DiagnosticWorker>(expectation,std::move(factory),binding->clock(),binding);
}
} // namespace sh3::observer
