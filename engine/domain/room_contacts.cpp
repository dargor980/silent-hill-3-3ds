#include "sh3/domain/room_contacts.hpp"
#include <algorithm>
#include <cstring>
#include <limits>

namespace sh3::domain {
namespace {
static_assert(sizeof(float) == 4 && std::numeric_limits<float>::is_iec559);
// Keep heavy helper frames separate so stack-usage reports give a bounded call graph.
#define HRC_NOINLINE __attribute__((noinline))
using Magnitude = std::array<std::uint32_t, 6>;
struct Integer { Magnitude words{}; bool negative{}; };
struct Ratio { Integer numerator{}; Magnitude denominator{{1}}; };
struct Bounds { Integer low[2], high[2]; };

std::uint32_t bits(float v) noexcept {
    std::uint32_t out;
    std::memcpy(&out, &v, sizeof(out));
    return out;
}
bool finite(float v) noexcept { return (bits(v) & 0x7f800000U) != 0x7f800000U; }
bool bounded(float v) noexcept { return (bits(v) & 0x7fffffffU) <= 0x49742400U; }
std::uint32_t ordered(float v) noexcept {
    auto raw = bits(v);
    if ((raw & 0x7fffffffU) == 0) raw = 0;
    return raw & 0x80000000U ? ~raw : raw | 0x80000000U;
}
bool bounded(Vec3 v) noexcept { return bounded(v.x) && bounded(v.y) && bounded(v.z); }
bool finite(Vec3 v) noexcept { return finite(v.x) && finite(v.y) && finite(v.z); }
bool valid_box(const RoomContactBox &b) noexcept {
    return bounded(b.xmin) && bounded(b.xmax) && bounded(b.zmin) && bounded(b.zmax) &&
           ordered(b.xmin) <= ordered(b.xmax) && ordered(b.zmin) <= ordered(b.zmax);
}
template <std::size_t N>
HRC_NOINLINE int compare(const std::array<std::uint32_t, N> &a,
                         const std::array<std::uint32_t, N> &b) noexcept {
    for (std::size_t i = N; i-- > 0;) {
        if (a[i] != b[i]) return a[i] < b[i] ? -1 : 1;
    }
    return 0;
}
bool zero(const Magnitude &v) noexcept {
    std::uint32_t all = 0;
    for (auto word : v) all |= word;
    return all == 0;
}
Integer negate(Integer v) noexcept {
    v.negative = !v.negative && !zero(v.words);
    return v;
}
HRC_NOINLINE Integer integer(float v) noexcept {
    // Caller has checked |v| <= 1e6 by bits, including rejection of all NaNs.
    const auto raw = bits(v), exponent = (raw >> 23) & 255U;
    const auto mantissa = (raw & 0x7fffffU) | (exponent ? 0x800000U : 0U);
    const auto shift = exponent ? exponent - 1 : 0;
    const auto wide = std::uint64_t(mantissa) << (shift % 32);
    Integer out;
    out.words[shift / 32] = std::uint32_t(wide);
    out.words[shift / 32 + 1] = std::uint32_t(wide >> 32);
    out.negative = (raw >> 31) != 0 && mantissa != 0;
    return out;
}
HRC_NOINLINE int compare(const Integer &a, const Integer &b) noexcept {
    if (a.negative != b.negative) return a.negative ? -1 : 1;
    const auto result = compare(a.words, b.words);
    return a.negative ? -result : result;
}
HRC_NOINLINE Integer add(const Integer &a, const Integer &b) noexcept {
    Integer out;
    if (a.negative == b.negative) {
        std::uint64_t carry = 0;
        for (std::size_t i = 0; i < 6; ++i) {
            const auto sum = std::uint64_t(a.words[i]) + b.words[i] + carry;
            out.words[i] = std::uint32_t(sum);
            carry = sum >> 32;
        }
        out.negative = a.negative;
    } else {
        const bool a_larger = compare(a.words, b.words) >= 0;
        const auto &large = a_larger ? a : b;
        const auto &small = a_larger ? b : a;
        std::uint64_t borrow = 0;
        for (std::size_t i = 0; i < 6; ++i) {
            const auto sub = std::uint64_t(small.words[i]) + borrow;
            const auto word = std::uint64_t(large.words[i]);
            out.words[i] = std::uint32_t(word - sub);
            borrow = word < sub;
        }
        out.negative = large.negative && !zero(out.words);
    }
    return out;
}
Integer subtract(const Integer &a, const Integer &b) noexcept { return add(a, negate(b)); }
// Twelve limbs simplify full 6x6 multiplication; the twelfth is always zero
// for HRC's <2^170 operands. Products remain <2^340 (no truncation).
HRC_NOINLINE std::array<std::uint32_t, 12> product(const Magnitude &a,
                                                 const Magnitude &b) noexcept {
    std::array<std::uint32_t, 12> out{};
    for (std::size_t i = 0; i < 6; ++i) {
        std::uint64_t carry = 0;
        for (std::size_t j = 0; j < 6; ++j) {
            const auto value = std::uint64_t(a[i]) * b[j] + out[i + j] + carry;
            out[i + j] = std::uint32_t(value);
            carry = value >> 32;
        }
        out[i + 6] = std::uint32_t(carry);
    }
    return out;
}
HRC_NOINLINE int compare(const Ratio &a, const Ratio &b) noexcept {
    if (a.numerator.negative != b.numerator.negative) return a.numerator.negative ? -1 : 1;
    const auto left = product(a.numerator.words, b.denominator);
    const auto right = product(b.numerator.words, a.denominator);
    const auto result = compare(left, right);
    return a.numerator.negative ? -result : result;
}
HRC_NOINLINE Bounds bounds(const RoomContactBox &box, bool floor) noexcept {
    auto radius = integer(176);
    if (!floor) radius = negate(radius);
    return {{add(integer(box.xmin), radius), add(integer(box.zmin), radius)},
            {subtract(integer(box.xmax), radius), subtract(integer(box.zmax), radius)}};
}
HRC_NOINLINE bool inside(const Integer (&point)[2], const Bounds &b, bool strict) noexcept {
    for (unsigned axis = 0; axis < 2; ++axis) {
        const auto low = compare(point[axis], b.low[axis]);
        const auto high = compare(point[axis], b.high[axis]);
        if (strict ? low <= 0 || high >= 0 : low < 0 || high > 0) return false;
    }
    return true;
}
HRC_NOINLINE bool touches(const Integer (&from)[2], const Integer (&delta)[2],
                          const Bounds &box) noexcept {
    Ratio lo, hi;
    hi.numerator.words[0] = 1;
    for (unsigned axis = 0; axis < 2; ++axis) {
        const auto &d = delta[axis];
        if (zero(d.words)) {
            if (compare(from[axis], box.low[axis]) < 0 ||
                compare(from[axis], box.high[axis]) > 0) return false;
        } else {
            const auto &near = d.negative ? box.high[axis] : box.low[axis];
            const auto &far = d.negative ? box.low[axis] : box.high[axis];
            Ratio entry{subtract(near, from[axis]), d.words};
            Ratio exit{subtract(far, from[axis]), d.words};
            if (d.negative) {
                entry.numerator = negate(entry.numerator);
                exit.numerator = negate(exit.numerator);
            }
            if (compare(entry, lo) > 0) lo = entry;
            if (compare(exit, hi) < 0) hi = exit;
            if (compare(lo, hi) > 0) return false;
        }
    }
    return true;
}
} // namespace

RoomContactError RoomContactScene::prepare(const RoomContactInput &input,
                                          RoomContactMemory memory) noexcept {
    using Error = RoomContactError;
    if (input.profile != RoomContactProfile::static_xz_aabb_stop_v1 ||
        bits(input.half_extent) != bits(175) || bits(input.guard) != bits(1))
        return Error::unsupported_profile;
    if (input.blocker_count > room_contact_capacity) return Error::capacity_exceeded;
    const auto resident = std::max(memory.resident_bytes, room_contact_resident_bound);
    const auto scratch = std::max(memory.scratch_bytes, room_contact_stack_bound);
    if (resident > room_contact_budget || scratch > room_contact_budget - resident)
        return Error::budget_exceeded;
    if (!bounded(input.origin) || !bounded(input.floor_y) || !valid_box(input.floor) ||
        (input.blocker_count != 0 && input.blockers == nullptr)) return Error::invalid_geometry;
    for (std::size_t i = 0; i < input.blocker_count; ++i)
        if (!valid_box(input.blockers[i])) return Error::invalid_geometry;
    const auto floor = bounds(input.floor, true);
    if (compare(floor.low[0], floor.high[0]) >= 0 || compare(floor.low[1], floor.high[1]) >= 0)
        return Error::empty_floor;

    RoomContactScene staged;
    staged.floor_ = input.floor;
    staged.origin_ = input.origin;
    staged.floor_y_ = input.floor_y;
    staged.count_ = static_cast<std::uint32_t>(input.blocker_count);
    for (std::size_t i = 0; i < input.blocker_count; ++i) staged.boxes_[i] = input.blockers[i];
    staged.ready_ = true;
    *this = staged;
    return Error::ok;
}

RoomContactError RoomContactScene::resolve(Vec3 from, Vec3 requested, Vec3 &accepted) const noexcept {
    using Error = RoomContactError;
    if (!ready_) return Error::unavailable;
    if (!finite(from) || !finite(requested)) return Error::invalid_query;
    if (!bounded(from) || !bounded(requested)) return Error::out_of_bounds;
    if (ordered(from.y) != ordered(floor_y_) || ordered(requested.y) != ordered(floor_y_))
        return Error::off_floor;
    const Integer start[]{integer(from.x), integer(from.z)};
    const Integer end[]{integer(requested.x), integer(requested.z)};
    const Integer delta[]{subtract(end[0], start[0]), subtract(end[1], start[1])};
    const auto floor = bounds(floor_, true);
    if (!inside(start, floor, true)) return Error::invalid_start;
    bool blocked = !inside(end, floor, true);
    for (std::uint32_t i = 0; i < count_; ++i) {
        const auto box = bounds(boxes_[i], false);
        // Validate every starting overlap even if an earlier box already blocked the sweep.
        if (inside(start, box, false)) return Error::invalid_start;
        if (!blocked && touches(start, delta, box)) blocked = true;
    }
    const auto &chosen = blocked ? from : requested;
    std::memcpy(&accepted, &chosen, sizeof(accepted));
    return Error::ok;
}
#undef HRC_NOINLINE
} // namespace sh3::domain
