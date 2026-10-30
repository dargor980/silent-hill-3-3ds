#include "check.hpp"
#include "sh3/domain/inspection_movement.hpp"
#include <algorithm>
#include <cmath>
#include <complex>
#include <cstring>
#include <limits>
#include <new>

namespace { bool forbid_allocation = false; }
void *operator new(std::size_t n) {
    if (forbid_allocation)
        std::abort();
    if (auto *p = std::malloc(n ? n : 1))
        return p;
    throw std::bad_alloc();
}
void *operator new[](std::size_t n) { return ::operator new(n); }
void operator delete(void *p) noexcept { std::free(p); }
void operator delete(void *p, std::size_t) noexcept { std::free(p); }
void operator delete[](void *p) noexcept { std::free(p); }
void operator delete[](void *p, std::size_t) noexcept { std::free(p); }

namespace {
using namespace sh3::domain;
using Motion = InspectionMotion;
using Turn = InspectionTurn;
using Error = InspectionMovementError;
constexpr float pi = inspection_movement_pi;
constexpr auto maximum = std::numeric_limits<std::uint32_t>::max();

void near(double actual, double expected, double tolerance = .01) {
    CHECK(std::isfinite(actual) && std::abs(actual - expected) <= tolerance);
}
InspectionMovementPlan step(const InspectionMovementState &s, Motion motion, Turn turn) {
    InspectionMovementPlan out;
    CHECK(plan_inspection_movement(s, {motion, turn}, 2, out) == Error::ok);
    return out;
}
bool same(const InspectionMovementState &a, const InspectionMovementState &b) {
    return a.position.x == b.position.x && a.position.y == b.position.y &&
           a.position.z == b.position.z && a.yaw == b.yaw && a.ordinal == b.ordinal;
}
void rejected(InspectionMovementState s, InspectionMovementIntent intent,
              std::uint32_t ticks, Error error) {
    auto out = step({{7, -9, 11}, .7F, 17}, Motion::run, Turn::left);
    std::array<unsigned char, sizeof(out)> before{};
    std::array<unsigned char, sizeof(s)> input{};
    std::memcpy(before.data(), &out, sizeof(out));
    std::memcpy(input.data(), &s, sizeof(s));
    CHECK(plan_inspection_movement(s, intent, ticks, out) == error);
    CHECK(std::memcmp(before.data(), &out, sizeof(out)) == 0);
    CHECK(std::memcmp(input.data(), &s, sizeof(s)) == 0);
}
void failures() {
    const auto nan = std::numeric_limits<float>::quiet_NaN();
    const auto inf = std::numeric_limits<float>::infinity();
    for (auto member : {&Vec3::x, &Vec3::y, &Vec3::z}) {
        for (auto value : {nan, inf, -inf, 1000001.F, -1000001.F}) {
            InspectionMovementState s{};
            s.position.*member = value;
            rejected(s, {}, 2, Error::invalid_state);
        }
    }
    for (auto yaw : {nan, inf, -inf, pi, pi + 1, -pi - 1})
        rejected({{}, yaw, 0}, {}, 2, Error::invalid_state);
    for (auto invalid : {-1, 3, 4, 2147483647}) {
        rejected({}, {static_cast<Motion>(invalid), Turn::none}, 2, Error::invalid_intent);
        rejected({}, {Motion::idle, static_cast<Turn>(invalid)}, 2, Error::invalid_intent);
    }
    for (auto ticks : {0U, 1U, 3U, maximum})
        rejected({}, {}, ticks, Error::invalid_ticks);
    rejected({{}, 0, maximum}, {}, 2, Error::ordinal_exhausted);
    // Precedence is part of the error contract.
    rejected({{}, nan, maximum}, {static_cast<Motion>(9), Turn::none}, 0, Error::invalid_state);
    rejected({{}, 0, maximum}, {static_cast<Motion>(9), Turn::none}, 0, Error::invalid_intent);
    rejected({{}, 0, maximum}, {}, 0, Error::invalid_ticks);
    for (auto sign : {-1.F, 1.F}) {
        rejected({{sign * 1000000, 0, 0}, sign * pi / 2, 0},
                 {Motion::run, Turn::none}, 2, Error::out_of_bounds);
        rejected({{0, 0, sign * 1000000}, sign > 0 ? 0 : -pi, 0},
                 {Motion::run, Turn::none}, 2, Error::out_of_bounds);
        const auto boundary = step({{sign * 1000000, sign * 1000000, sign * 1000000},
                                     -pi, maximum - 1}, Motion::idle, Turn::none);
        CHECK(boundary.next.ordinal == maximum);
        near(boundary.next.position.x, sign * 1000000, 0);
        near(boundary.next.position.y, sign * 1000000, 0);
        near(boundary.next.position.z, sign * 1000000, 0);
    }
}

void analytical_vectors() {
    // Double precision complex rotation is an independent geometric oracle.
    for (auto yaw : {-pi, -pi + .01F, -pi / 2, -.5412034988F, 0.F,
                     .0724030137F, pi / 2, pi - .01F}) {
        for (auto motion : {Motion::idle, Motion::walk, Motion::run}) {
            for (auto turn : {Turn::none, Turn::left, Turn::right}) {
                const InspectionMovementState start{{-27175.5F, .11531066F, 21164.64F}, yaw, 27};
                const auto plan = step(start, motion, turn);
                const double distance = motion == Motion::idle ? 0 : motion == Motion::walk ? 28 : 70;
                const auto delta = std::polar(distance, double(yaw));
                near(plan.displacement.x, delta.imag(), .00002);
                near(plan.displacement.z, delta.real(), .00002);
                CHECK(plan.displacement.y == 0);
                near(plan.next.position.x, double(start.position.x) + delta.imag());
                near(plan.next.position.z, double(start.position.z) + delta.real());
                CHECK(plan.next.position.y == start.position.y && plan.next.ordinal == 28);
                const double angle = double(yaw) +
                    (turn == Turn::none ? 0 : turn == Turn::left ? -double(.088F) : double(.088F));
                const double expected_yaw = angle - 2 * double(pi) *
                    std::floor((angle + double(pi)) / (2 * double(pi)));
                near(plan.next.yaw, expected_yaw, 3e-7);
                CHECK(plan.next.yaw >= -pi && plan.next.yaw < pi);
                const auto rotation = std::polar(1.0, expected_yaw);
                // Transform a nonzero local point. Translation appears only once.
                const auto point = std::complex<double>(5, 2) * rotation;
                const auto &m = plan.model;
                near(2 * m[0] + 5 * m[8] + m[12], point.imag() + plan.next.position.x);
                near(3 * m[5] + m[13], 3 + double(start.position.y));
                near(2 * m[2] + 5 * m[10] + m[14], point.real() + plan.next.position.z);
                near(m[0], rotation.real(), 1e-6);
                near(m[2], -rotation.imag(), 1e-6);
                near(m[8], rotation.imag(), 1e-6);
                near(m[10], rotation.real(), 1e-6);
                CHECK(m[1] == 0 && m[4] == 0 && m[6] == 0 && m[9] == 0);
                CHECK(m[3] == 0 && m[7] == 0 && m[11] == 0 && m[15] == 1);
                CHECK(m[12] == plan.next.position.x && m[13] == plan.next.position.y &&
                      m[14] == plan.next.position.z);
                PoseMatrix rebuilt;
                CHECK(make_inspection_movement_model(plan.next.position, plan.next.yaw, rebuilt));
                CHECK(rebuilt == m);
            }
        }
    }
    // Basic axis vectors and the observed translate-before-turn order.
    const auto walk = step({}, Motion::walk, Turn::right);
    CHECK(walk.next.position.x == 0 && walk.next.position.z == 28);
    CHECK(walk.next.yaw == .088F);
    const auto run = step({{}, pi / 2, 0}, Motion::run, Turn::none);
    near(run.next.position.x, 70, .00001);
    near(run.next.position.z, 0, .00001);
    // Y includes signed zero; no floor snap is allowed in the planner.
    const InspectionMovementState signed_y{{0, -0.F, 0}, 0, 0};
    CHECK(std::signbit(step(signed_y, Motion::walk, Turn::left).next.position.y));

    auto reused = step({}, Motion::walk, Turn::none);
    const auto expected = step(reused.next, Motion::run, Turn::right);
    CHECK(plan_inspection_movement(reused.next, {Motion::run, Turn::right}, 2, reused) == Error::ok);
    CHECK(same(reused.next, expected.next) && reused.model == expected.model);
    std::array<unsigned char, sizeof(reused)> before{};
    std::memcpy(before.data(), &reused, sizeof(reused));
    CHECK(plan_inspection_movement(reused.next, {}, 0, reused) == Error::invalid_ticks);
    CHECK(std::memcmp(before.data(), &reused, sizeof(reused)) == 0);
}

void placement_failures() {
    PoseMatrix out;
    CHECK(make_inspection_movement_model({17, -3, 29}, .8F, out));
    const auto before = out;
    const auto nan = std::numeric_limits<float>::quiet_NaN();
    const auto inf = std::numeric_limits<float>::infinity();
    for (auto member : {&Vec3::x, &Vec3::y, &Vec3::z}) {
        for (float value : {nan, inf, -inf, 1000001.F, -1000001.F}) {
            Vec3 position{}; position.*member = value;
            CHECK(!make_inspection_movement_model(position, 0, out));
            CHECK(std::memcmp(out.data(), before.data(), sizeof(out)) == 0);
        }
    }
    for (float yaw : {nan, inf, -inf, pi, -pi - 1}) {
        CHECK(!make_inspection_movement_model({}, yaw, out));
        CHECK(std::memcmp(out.data(), before.data(), sizeof(out)) == 0);
    }
}

InspectionMovementState replay(const std::array<unsigned, 4> &cadence) {
    InspectionMovementState state{{12, -7, 23}, 0, 0};
    unsigned elapsed = 0, pending = 0, frame = 0;
    while (elapsed < 4000) {
        // Test harness only: presentation is not a production scheduler.
        const auto interval = std::min(cadence[frame++ % cadence.size()], 4000 - elapsed);
        elapsed += interval;
        pending += interval;
        while (pending >= inspection_movement_step_ms) {
            const auto i = state.ordinal;
            const auto motion = i < 20 ? Motion::idle : i < 60 ? Motion::walk : Motion::run;
            const auto turn = i < 40 ? Turn::left : i < 80 ? Turn::right : Turn::none;
            state = step(state, motion, turn).next;
            pending -= inspection_movement_step_ms;
        }
    }
    CHECK(state.ordinal == 100 && pending == 0 && state.position.y == -7);
    return state;
}
} // namespace

int main() {
    static_assert(sizeof(InspectionMovementState) + sizeof(InspectionMovementPlan) <= 128);
    forbid_allocation = true;
    failures();
    analytical_vectors();
    placement_failures();
    const auto reference = replay({40, 40, 40, 40});
    CHECK(same(reference, replay({16, 17, 16, 17})));
    CHECK(same(reference, replay({3, 71, 7, 119})));
    CHECK(same(reference, replay({4000, 4000, 4000, 4000})));
    forbid_allocation = false;
    std::puts("Inspection movement: analytical vectors, rejection rollback, aliasing and tick replays passed");
}
