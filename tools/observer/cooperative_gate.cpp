#include "sh3_observer/cooperative_gate.hpp"
#include <new>

namespace sh3::observer {
CooperativeGate::Token::~Token() { if (owner) owner->leave(); }
CooperativeGate::Work CooperativeGate::enter() noexcept {
  std::shared_ptr<Token> token;
  try { token = std::make_shared<Token>(); }
  catch (const std::bad_alloc&) { return {}; }
  const std::lock_guard<std::mutex> lock(mutex_);
  if (closed_ || active_ == capacity_) return {};
  ++active_;
  token->owner = this;
  return Work(std::move(token));
}
void CooperativeGate::leave() noexcept {
  const std::lock_guard<std::mutex> lock(mutex_);
  --active_;
}
CooperativeGate::Closure::Closure(CooperativeGate& gate, Clock::time_point deadline) noexcept
  : gate_(gate), deadline_(deadline) {
  const std::lock_guard<std::mutex> lock(gate_.mutex_);
  if (!gate_.closed_) {
    gate_.closed_ = true;
    owns_ = true;
    state_ = State::draining;
  }
}
CooperativeGate::Closure::~Closure() { cancel(); }
CooperativeGate::State CooperativeGate::Closure::poll() noexcept {
  if (!owns_) return state_;
  const std::lock_guard<std::mutex> lock(gate_.mutex_);
  if (Clock::now() >= deadline_) state_ = State::timed_out;
  else state_ = gate_.active_ == 0 ? State::held : State::draining;
  return state_;
}
void CooperativeGate::Closure::cancel() noexcept {
  if (!owns_) return;
  const std::lock_guard<std::mutex> lock(gate_.mutex_);
  gate_.closed_ = false;
  owns_ = false;
  state_ = State::cancelled;
}
} // namespace sh3::observer
