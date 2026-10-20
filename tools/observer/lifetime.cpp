#include "sh3_observer/lifetime.hpp"
#include "sh3_observer/capture.hpp"
#include <algorithm>
#include <limits>

namespace sh3::observer {
namespace {
struct Range { std::uint32_t offset, size; };
bool valid(Range r) noexcept {
  return r.size > 0 && r.size <= ram_size && r.offset <= ram_size - r.size;
}
bool overlaps(Range a, Range b) noexcept {
  return std::uint64_t{a.offset} < std::uint64_t{b.offset} + b.size &&
    std::uint64_t{b.offset} < std::uint64_t{a.offset} + a.size;
}
bool valid_plan(const LifetimePlan& p) noexcept {
  if (!std::any_of(p.begin.session.begin(), p.begin.session.end(), [](auto v) {return v != 0;}) ||
      !p.begin.epoch || !p.begin.serial || !p.limit || p.limit > lifetime_max_notices ||
      p.begin.serial > std::numeric_limits<std::uint64_t>::max() - p.limit) return false;
  const std::array<Range, 4> ranges{{{p.target.root, 4}, {p.target.pool, 24},
                                  {p.target.object, 48}, {p.target.vtable, 12}}};
  for (std::size_t i = 0; i < ranges.size(); ++i) {
    if (!valid(ranges[i]) || ranges[i].offset % 4 != 0) return false;
    for (std::size_t j = 0; j < i; ++j)
      if (overlaps(ranges[i], ranges[j])) return false;
  }
  return true;
}
LifetimeReason lifecycle_reason(LifetimeKind kind) noexcept {
  switch (kind) {
    case LifetimeKind::reset: return LifetimeReason::reset;
    case LifetimeKind::restore: return LifetimeReason::restore;
    case LifetimeKind::remap: return LifetimeReason::remap;
    case LifetimeKind::settings: return LifetimeReason::settings;
    case LifetimeKind::lost: return LifetimeReason::lost;
    case LifetimeKind::shutdown: return LifetimeReason::shutdown;
    case LifetimeKind::cancel: return LifetimeReason::cancelled;
    default: return LifetimeReason::protocol;
  }
}
} // namespace

bool LifetimeGuard::fail(LifetimeReason reason) noexcept {
  report_.state = LifetimeState::failed;
  report_.reason = reason;
  return false;
}
bool LifetimeGuard::arm(const LifetimePlan& p) noexcept {
  if (report_.state == LifetimeState::failed || report_.state == LifetimeState::sealed) return false;
  if (report_.state != LifetimeState::idle) return fail(LifetimeReason::protocol);
  if (!valid_plan(p)) return fail(LifetimeReason::plan);
  plan_ = p;
  report_.begin = report_.last = p.begin;
  report_.state = LifetimeState::armed;
  return true;
}
bool LifetimeGuard::notify(const LifetimeNotice& n) noexcept {
  if (report_.state == LifetimeState::failed || report_.state == LifetimeState::sealed) return false;
  if (report_.state != LifetimeState::armed) return fail(LifetimeReason::protocol);
  if (n.stamp.session != plan_.begin.session) return fail(LifetimeReason::identity);
  if (n.stamp.epoch != plan_.begin.epoch) return fail(LifetimeReason::epoch);
  if (report_.accepted >= plan_.limit) return fail(LifetimeReason::budget);
  if (n.stamp.serial != report_.last.serial + 1) return fail(LifetimeReason::sequence);
  if (n.stamp.cycle < report_.last.cycle ||
      n.stamp.cycle - plan_.begin.cycle > lifetime_max_cycles) return fail(LifetimeReason::cycle);
  if (n.kind == LifetimeKind::write) {
    const Range write{n.offset, n.size};
    if (!valid(write)) return fail(LifetimeReason::range);
    const auto t = plan_.target;
    const std::array<Range, 5> watched{{{t.root, 4}, {t.pool, 24}, {t.object, 32},
                                     {t.object + 36, 8}, {t.vtable, 12}}};
    for (const auto range : watched)
      if (overlaps(write, range)) return fail(LifetimeReason::protected_write);
    ++report_.writes;
  } else {
    if (n.offset || n.size) return fail(LifetimeReason::protocol);
    if (n.kind == LifetimeKind::checkpoint) ++report_.checkpoints;
    else if (n.kind == LifetimeKind::finish) {
      if (n.stamp.cycle == plan_.begin.cycle) return fail(LifetimeReason::cycle);
      report_.state = LifetimeState::sealed;
    } else return fail(lifecycle_reason(n.kind));
  }
  report_.last = n.stamp;
  ++report_.accepted;
  return true;
}
} // namespace sh3::observer
