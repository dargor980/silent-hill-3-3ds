#include "sh3_observer/diagnostic_worker.hpp"
#include "check.hpp"
#include <atomic>
#include <thread>

using namespace sh3::observer;
using namespace std::chrono_literals;
namespace {
using Clock = DiagnosticClock::Clock;
class TimedWork final : public DiagnosticWork {
public:
  explicit TimedWork(DiagnosticExpectation policy) : policy_(policy) {}
  DiagnosticRejection prepare(DiagnosticBudget& budget) override {
    CHECK(budget.remaining() > 0s && budget.remaining() <= 5s);
    return DiagnosticRejection::none;
  }
  DiagnosticRejection sample(DiagnosticBudget& budget, DiagnosticObservation& out) override {
    if (++samples_ == 2) {
      CHECK(budget.remaining() > 0s && budget.remaining() <= 2s);
      // A cooperative provider returns after observing the deadline itself.
      while (budget.checkpoint()) std::this_thread::sleep_for(1ms);
      CHECK(budget.remaining() == 0s);
      return DiagnosticRejection::cancelled; // First cause must remain deadline.
    }
    auto& r = out.inventory;
    r.profile = policy_.profile; r.scope = IdentityScope::application_headers;
    r.platform_assumed = true; r.process.pid = 1; r.process.birth_ns = 1;
    r.process.nonce.fill(1); r.file_objects.fill(2); r.classified_images.fill(3);
    r.policy_evidence = policy_.policy_evidence; r.application_evidence = policy_.application_evidence;
    r.platform_evidence = policy_.platform_evidence; r.loader_revision = 1; r.application_images = 1;
    return DiagnosticRejection::none;
  }
  bool close() noexcept override { return true; }
private:
  const DiagnosticExpectation policy_;
  unsigned samples_{};
};
class Factory final : public DiagnosticWorkFactory {
public:
  explicit Factory(DiagnosticExpectation policy) : policy_(policy) {}
  std::unique_ptr<DiagnosticWork> create(DiagnosticBudget& budget) override {
    CHECK(budget.checkpoint()); return std::make_unique<TimedWork>(policy_);
  }
private:
  const DiagnosticExpectation policy_;
};
}
int main() {
  DiagnosticExpectation policy{IdentityProfile::macos_platform_slices_v2,{},{},{}};
  policy.policy_evidence.fill(1); policy.application_evidence.fill(2); policy.platform_evidence.fill(3);
  DiagnosticRequest request; request.challenge.fill(1); request.sequence = 1;
  DiagnosticCompletion out;
  {
    DiagnosticWorker worker(policy,std::make_unique<Factory>(policy));
    const auto start = Clock::now(); CHECK(worker.submit(request,{}));
    // No take/status call drives expiry: the parked mailbox enforces it itself.
    CHECK(worker.wait_stopped_until(start+7s)); CHECK(Clock::now()-start >= 5s);
    CHECK(worker.status().reason == DiagnosticRejection::deadline); CHECK(!worker.take(out));
  }
  {
    DiagnosticWorker worker(policy,std::make_unique<Factory>(policy));
    CHECK(worker.submit(request,{})); const auto until = Clock::now()+3s;
    while (!worker.take(out)) { CHECK(Clock::now() < until); std::this_thread::sleep_for(1ms); }
    request.sequence = 2; const auto start = Clock::now(); CHECK(worker.submit(request,{}));
    CHECK(worker.wait_stopped_until(start+4s)); CHECK(Clock::now()-start >= 2s);
    CHECK(worker.status().reason == DiagnosticRejection::deadline); CHECK(!worker.take(out));
  }
}
