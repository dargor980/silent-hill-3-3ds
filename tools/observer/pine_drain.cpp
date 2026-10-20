#include "sh3_observer/pine_drain.hpp"

namespace sh3::observer {
PineDrain::~PineDrain() { cancel(request_.id); retire(); }
bool PineDrain::terminal() const noexcept {
  return state_ != State::idle && state_ != State::queued &&
         state_ != State::draining && state_ != State::held;
}
bool PineDrain::submit(Request request) noexcept {
  if (active() || !request.id || request.id <= last_id_ || !request.identity.vm ||
      !request.identity.server || request.deadline <= Clock::now()) return false;
  request_ = request;
  last_id_ = request.id;
  state_ = State::queued;
  return true;
}
PineDrain::State PineDrain::step(bool paused, Identity current) noexcept {
  if (!active() || terminal()) return state_;
  if (!cpu_.at_boundary() || !paused || !current.vm || !current.server ||
      current.vm != request_.identity.vm || current.server != request_.identity.server) {
    state_ = State::invalidated;
  } else if (Clock::now() >= request_.deadline) {
    state_ = State::timed_out;
  } else {
    if (!lease_) lease_.emplace(source_, request_.deadline);
    switch (lease_->closure.poll()) {
    case CooperativeGate::State::held: state_ = State::held; break;
    case CooperativeGate::State::draining: state_ = State::draining; break;
    case CooperativeGate::State::timed_out: state_ = State::timed_out; break;
    default: state_ = State::rejected; break;
    }
  }
  return state_;
}
bool PineDrain::complete(bool paused, Identity identity) noexcept {
  if (step(paused, identity) != State::held) return false;
  state_ = State::completed;
  return true;
}
bool PineDrain::cancel(std::uint64_t id) noexcept {
  if (!active() || terminal() || id != request_.id) return false;
  state_ = State::cancelled;
  return true;
}
PineDrain::Result PineDrain::retire() noexcept {
  if (!terminal()) return {};
  const Result result = status();
  // Terminal status is already visible before the destructor reopens the gate.
  lease_.reset();
  request_ = {};
  state_ = State::idle;
  return result;
}
} // namespace sh3::observer
