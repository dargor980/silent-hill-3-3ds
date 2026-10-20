#include "sh3_observer/cpu_boundary.hpp"

namespace sh3::observer {
void CpuBoundary::invalidate() noexcept {
  if (boundary_) boundary_->valid_ = false;
}
void CpuBoundary::set_online(bool online) noexcept {
  invalidate();
  online_ = online;
}
CpuBoundary::Activity::Activity(CpuBoundary& owner) noexcept
    : owner_(owner), was_busy_(owner.busy_) {
  owner_.invalidate();
  owner_.busy_ = true;
}
CpuBoundary::Activity::~Activity() { owner_.busy_ = was_busy_; }
CpuBoundary::Boundary::Boundary(CpuBoundary& owner) noexcept : owner_(owner) {
  owner_.invalidate();
  if (!owner_.online_ || owner_.busy_ || owner_.boundary_) return;
  owner_.boundary_ = this;
  valid_ = true;
}
CpuBoundary::Boundary::~Boundary() {
  if (owner_.boundary_ == this) owner_.boundary_ = nullptr;
}
} // namespace sh3::observer
