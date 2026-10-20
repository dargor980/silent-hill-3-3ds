#include "sh3_observer/retained_drain.hpp"

namespace sh3::observer {
RetainedDrain::~RetainedDrain() { cancel(request_.id); retire(); }
bool RetainedDrain::terminal() const noexcept {
  return state_ != State::idle && state_ != State::queued &&
         state_ != State::draining && state_ != State::held;
}
RetainedDrain::State RetainedDrain::stop(State state) noexcept {
  state_ = state;
  pine_.cancel(request_.id);
  return state_;
}
bool RetainedDrain::submit(Request request) noexcept {
  if (active() || stepping_ || retiring_ || !pine_.submit(request)) return false;
  request_ = request;
  state_ = State::queued;
  return true;
}
RetainedDrain::State RetainedDrain::step(bool paused, Identity identity) noexcept {
  if (!active() || terminal()) return state_;
  if (stepping_) return stop(State::invalidated);
  struct StepScope {
    bool& flag;
    explicit StepScope(bool& value) : flag(value) { flag = true; }
    ~StepScope() { flag = false; }
  } scope(stepping_);
  const auto pine_state = pine_.step(paused, identity);
  if (pine_state != State::held) {
    state_ = pine_state;
    return state_;
  }
  if (!started_) {
    started_ = true; // Even a partially failed begin requires release.
    effects_.begin(request_);
    if (terminal()) return state_;
  }
  const auto progress = effects_.poll(request_.id);
  if (terminal()) return state_;
  // A port must not dispatch, but still reject revoked scope or expired time.
  const auto revalidated = pine_.step(paused, identity);
  if (revalidated != State::held) return stop(revalidated);
  switch (progress) {
  case EffectDrainPort::Progress::pending: state_ = State::draining; break;
  case EffectDrainPort::Progress::held: state_ = State::held; break;
  default: return stop(State::rejected);
  }
  return state_;
}
bool RetainedDrain::complete(bool paused, Identity identity) noexcept {
  if (state_ != State::held || step(paused, identity) != State::held) return false;
  if (!pine_.complete(paused, identity)) {
    state_ = pine_.status().state;
    return false;
  }
  state_ = State::completed;
  return true;
}
bool RetainedDrain::cancel(std::uint64_t id) noexcept {
  if (!active() || terminal() || id != request_.id) return false;
  stop(State::cancelled);
  return true;
}
RetainedDrain::Result RetainedDrain::retire() noexcept {
  if (!terminal() || stepping_ || retiring_) return {};
  retiring_ = true;
  const auto result = status();
  // Terminal is observable; PINE remains closed throughout release.
  if (started_) effects_.release(request_.id);
  started_ = false;
  pine_.retire();
  request_ = {};
  state_ = State::idle;
  retiring_ = false;
  return result;
}
} // namespace sh3::observer
