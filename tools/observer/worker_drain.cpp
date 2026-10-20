#include "sh3_observer/worker_drain.hpp"
#include <algorithm>

namespace sh3::observer {
WorkerDrain::WorkerDrain(WorkerPort& vu, WorkerPort& gs, std::uint32_t budget) noexcept
    : vu_(vu), gs_(gs), budget_(std::min(budget, WorkerControl::max_request_id)) {}
WorkerDrain::~WorkerDrain() { release(attempt_.id); }

bool WorkerDrain::sessions_match() const noexcept {
  const auto vu = vu_.lifecycle();
  const auto gs = gs_.lifecycle();
  return vu.online && gs.online && vu.generation == vu_session_.generation &&
         gs.generation == gs_session_.generation;
}

void WorkerDrain::begin(PineDrain::Request request) noexcept {
  // A second begin must not overwrite the tokens of a live attempt.
  if (attempt_.id || !request.id) return;
  attempt_ = request;
  progress_ = Progress::rejected;
  if (request.id <= last_attempt_) return;
  last_attempt_ = request.id;
  if (!request.identity.vm || !request.identity.server ||
      PineDrain::Clock::now() >= request.deadline || last_ticket_ >= budget_) return;
  vu_session_ = vu_.lifecycle();
  gs_session_ = gs_.lifecycle();
  if (!vu_session_.online || !gs_session_.online || !vu_session_.generation ||
      !gs_session_.generation) return;
  // Deliberately independent of the 64-bit attempt ID. Never wrap or reset on
  // a worker restart. A conflicting diagnostic token fails at the port.
  const WorkerControl::Token token{vu_session_.generation, ++last_ticket_};
  if (!vu_.request(token)) return;
  vu_token_ = token;
  progress_ = Progress::pending;
}

EffectDrainPort::Progress WorkerDrain::poll(std::uint64_t id) noexcept {
  if (!id || id != attempt_.id) return Progress::rejected;
  if (progress_ == Progress::rejected) return progress_;
  if (PineDrain::Clock::now() >= attempt_.deadline || !sessions_match())
    return progress_ = Progress::rejected;
  const auto vu = vu_.status(vu_token_);
  if (vu == WorkerControl::Status::pending && !gs_token_.id) return Progress::pending;
  if (vu != WorkerControl::Status::held) return progress_ = Progress::rejected;
  if (!gs_token_.id) {
    const WorkerControl::Token token{gs_session_.generation, last_ticket_};
    if (!gs_.request(token)) return progress_ = Progress::rejected;
    gs_token_ = token;
  }
  const auto gs = gs_.status(gs_token_);
  // Recheck after the last request/query, including VU which must remain held.
  if (!sessions_match() || vu_.status(vu_token_) != WorkerControl::Status::held ||
      PineDrain::Clock::now() >= attempt_.deadline)
    return progress_ = Progress::rejected;
  if (gs == WorkerControl::Status::pending) return progress_ = Progress::pending;
  if (gs == WorkerControl::Status::held) return progress_ = Progress::held;
  return progress_ = Progress::rejected;
}

void WorkerDrain::release(std::uint64_t id) noexcept {
  if (!id || id != attempt_.id) return;
  if (gs_token_.id) gs_.release(gs_token_);
  if (vu_token_.id) vu_.release(vu_token_);
  gs_token_ = {};
  vu_token_ = {};
  attempt_ = {};
  progress_ = Progress::rejected;
}
} // namespace sh3::observer
