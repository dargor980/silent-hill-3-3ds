#include "check.hpp"
#include "movement_fixture.hpp"
#include "sh3/platform/room_movement_contacts.hpp"
#include <cstring>
#include <iostream>
#include <limits>
#include <new>
#include <string>

namespace { bool forbid_allocation = false; }
void *operator new(std::size_t n) {
    if (forbid_allocation) std::abort();
    if (auto *p = std::malloc(n ? n : 1)) return p;
    throw std::bad_alloc();
}
void *operator new[](std::size_t n) { return ::operator new(n); }
void operator delete(void *p) noexcept { std::free(p); }
void operator delete(void *p, std::size_t) noexcept { std::free(p); }
void operator delete[](void *p) noexcept { std::free(p); }
void operator delete[](void *p, std::size_t) noexcept { std::free(p); }

namespace {
using namespace sh3;
using Error = domain::RoomContactError;
using Status = ports::MovementContactStatus;
using Scene = domain::RoomContactScene;
using Adapter = platform::RoomMovementContacts;
using Box = domain::RoomContactBox;
using Input = domain::RoomContactInput;
using Vec = domain::Vec3;
template <class T> auto bytes(const T &object) {
    std::array<unsigned char, sizeof(T)> result;
    std::memcpy(result.data(), static_cast<const void *>(&object), sizeof(T));
    return result;
}
std::uint32_t bits(float value) {
    std::uint32_t result;
    std::memcpy(&result, &value, 4);
    return result;
}
Vec sentinel() {
    const unsigned char raw[]{0xa5,0x5a,0xc3,0x3c,0x96,0x69,0x69,0x96,0x3c,0xc3,0x5a,0xa5};
    static_assert(sizeof(Vec) == sizeof(raw));
    Vec out;
    std::memcpy(&out, raw, sizeof(out));
    return out;
}
Input input(const Box *boxes = nullptr, std::size_t count = 0) {
    Input result;
    result.floor = {-1000, 1000, -1000, 1000};
    result.blockers = boxes; result.blocker_count = count;
    return result;
}
void check_query(const Scene &scene, const Adapter &adapter, ports::MovementContactQuery query,
                 Error &error, Status &status, Vec &result) {
    const auto scene_before = bytes(scene);
    const auto adapter_before = bytes(adapter);
    const auto original = query;
    const auto untouched = sentinel();
    result = untouched;
    error = scene.resolve(query.from, query.requested, result);
    auto via_port = untouched;
    status = adapter.resolve(query, via_port);
    CHECK(bytes(result) == bytes(via_port));
    if (error != Error::ok) CHECK(bytes(result) == bytes(untouched));
    for (unsigned repeat = 0; repeat < 2; ++repeat) {
        auto output = untouched;
        CHECK(scene.resolve(query.from, query.requested, output) == error);
        CHECK(bytes(output) == bytes(result));
        CHECK(adapter.resolve(query, output) == status);
        CHECK(bytes(output) == bytes(result));
    }
    for (bool alias_from : {true, false}) {
        query = original;
        auto &output = alias_from ? query.from : query.requested;
        const auto prior = bytes(output);
        CHECK(scene.resolve(query.from, query.requested, output) == error);
        CHECK(bytes(output) == (error == Error::ok ? bytes(result) : prior));
        query = original;
        CHECK(adapter.resolve(query, output) == status);
        CHECK(bytes(output) == (error == Error::ok ? bytes(result) : prior));
    }
    CHECK(bytes(scene) == scene_before && bytes(adapter) == adapter_before);
}
float read_float() {
    std::uint32_t raw;
    CHECK(bool(std::cin >> raw));
    float result;
    std::memcpy(&result, &raw, 4);
    return result;
}
Vec read_vec() { return {read_float(), read_float(), read_float()}; }
Box read_box() { return {read_float(), read_float(), read_float(), read_float()}; }
void vectors() {
    unsigned kind;
    while (std::cin >> kind) {
        unsigned profile, ready;
        Input data;
        domain::RoomContactMemory memory;
        CHECK(bool(std::cin >> profile));
        data.profile = static_cast<domain::RoomContactProfile>(profile);
        data.half_extent = read_float(); data.guard = read_float();
        data.origin = read_vec(); data.floor_y = read_float(); data.floor = read_box();
        CHECK(bool(std::cin >> data.blocker_count >> memory.resident_bytes >> memory.scratch_bytes));
        std::array<Box, 33> boxes{};
        CHECK(data.blocker_count <= boxes.size());
        for (std::size_t i = 0; i < data.blocker_count; ++i) boxes[i] = read_box();
        data.blockers = boxes.data();
        ports::MovementContactQuery query;
        CHECK(bool(std::cin >> ready));
        query.from = read_vec(); query.requested = read_vec();
        CHECK(bool(std::cin >> query.ordinal));
        Scene scene;
        Adapter adapter;
        Error prepared, resolved = Error::unavailable;
        Status status = Status::unavailable;
        auto output = sentinel();
        forbid_allocation = true;
        if (kind == 0) {
            CHECK(scene.prepare(input()) == Error::ok);
            CHECK(adapter.prepare(input()) == Error::ok);
            const auto old_scene = bytes(scene);
            const auto old_adapter = bytes(adapter);
            prepared = scene.prepare(data, memory);
            CHECK(adapter.prepare(data, memory) == prepared);
            if (prepared != Error::ok) {
                CHECK(bytes(scene) == old_scene && bytes(adapter) == old_adapter);
                Vec accepted;
                CHECK(scene.resolve({-500,0,0}, {500,0,0}, accepted) == Error::ok);
                CHECK(accepted.x == 500); // Previous empty scene remains usable.
            }
        } else {
            prepared = Error::ok;
            if (ready) {
                CHECK(scene.prepare(data) == Error::ok);
                CHECK(adapter.prepare(data) == Error::ok);
            }
            check_query(scene, adapter, query, resolved, status, output);
        }
        forbid_allocation = false;
        std::cout << unsigned(prepared) << ' ' << unsigned(resolved) << ' ' << unsigned(status)
                  << ' ' << bits(output.x) << ' ' << bits(output.y) << ' ' << bits(output.z) << '\n';
    }
    CHECK(std::cin.eof());
}
void ownership_and_failures() {
    Scene scene;
    Adapter adapter;
    Error error;
    Status status;
    Vec output;
    check_query(scene, adapter, {{-500,0,0},{500,0,0},0}, error, status, output);
    CHECK(error == Error::unavailable && status == Status::unavailable);
    auto bad = input(nullptr, 1);
    const auto empty_scene = bytes(scene);
    const auto empty_adapter = bytes(adapter);
    CHECK(scene.prepare(bad) == Error::invalid_geometry && !scene.ready());
    CHECK(adapter.prepare(bad) == Error::invalid_geometry && !adapter.ready());
    CHECK(bytes(scene) == empty_scene && bytes(adapter) == empty_adapter);
    bad.blocker_count = std::numeric_limits<std::size_t>::max();
    CHECK(scene.prepare(bad) == Error::capacity_exceeded);
    CHECK(scene.prepare(input(), {std::numeric_limits<std::size_t>::max(),1}) == Error::budget_exceeded);
    CHECK(scene.prepare(input(), {0,std::numeric_limits<std::size_t>::max()}) == Error::budget_exceeded);
    Box box{0,100,-100,100};
    CHECK(scene.prepare(input(&box,1), {0,0}) == Error::ok); // Reservations cannot understate bounds.
    CHECK(adapter.prepare(input(&box,1)) == Error::ok);
    box = {700,800,700,800}; // Caller-owned geometry no longer influences queries.
    check_query(scene, adapter, {{-500,0,0},{500,0,0},99}, error, status, output);
    CHECK(error == Error::ok && status == Status::accepted && output.x == -500);
    const Box overlaps[]{{0,100,-100,100}, {-600,-400,-100,100}};
    CHECK(scene.prepare(input(overlaps,2)) == Error::ok);
    CHECK(adapter.prepare(input(overlaps,2)) == Error::ok);
    check_query(scene, adapter, {{-500,0,0},{500,0,0},1}, error, status, output);
    CHECK(error == Error::invalid_start); // Later invalid start wins over earlier blocking hit.
}
void actor_and_controller() {
    using ActorError = application::InspectionActorError;
    using State = domain::SessionState;
    Adapter contacts;
    Box wall{-100,100,0,100};
    const auto config = input(&wall,1);
    CHECK(contacts.prepare(config) == Error::ok);
    const Vec spawn{0,0,-180};
    Vec validated;
    CHECK(contacts.resolve({spawn,spawn,0}, validated) == Status::accepted);
    CHECK(bytes(validated) == bytes(spawn));
    CHECK(contacts.resolve({{0,0,-176},{0,0,-176},0}, validated) == Status::unsupported);
    movement_test::Reader reader;
    application::MovementController controller(movement_test::profile, movement_test::rig(),
                                               reader, contacts, spawn, 0);
    CHECK(controller.ready());
    CHECK(controller.step({},0) == 0);
    application::MovementInput walk; walk.forward = true;
    CHECK(controller.step(walk,40000) == 1);
    const auto first = controller.snapshot();
    CHECK(bytes(first.movement.position) == bytes(spawn));
    CHECK(first.movement.ordinal == 1 && first.animation.clock.target_id == 109);
    walk.right = true;
    CHECK(controller.step(walk,40000) == 1);
    CHECK(bytes(controller.snapshot().movement.position) == bytes(spawn));
    CHECK(controller.snapshot().animation.clock.blend > first.animation.clock.blend);
    CHECK(controller.snapshot().movement.yaw > 0);
    CHECK(controller.snapshot().instance[14] == spawn.z);
    CHECK(controller.snapshot().animation.model[0][14] == -4); // Root remains model-local.

    const auto before = bytes(controller.snapshot());
    reader.fail = true;
    CHECK(controller.step(walk,40000) == 0);
    CHECK(controller.state() == State::paused && controller.remainder_us() == 0);
    CHECK(controller.result().error == ActorError::animation_rejected);
    CHECK(bytes(controller.snapshot()) == before);
    reader.fail = false;
    CHECK(controller.step({},0) == 0);
    application::MovementInput pause; pause.pause = true;
    CHECK(controller.step(pause,0) == 0);
    CHECK(controller.step({},0) == 0);
    CHECK(controller.step(walk,40000) == 1);
    CHECK(controller.snapshot().movement.ordinal == 3);

    auto raised = config; raised.floor_y = 1;
    CHECK(contacts.prepare(raised) == Error::ok);
    const auto before_contact = bytes(controller.snapshot());
    const auto calls = reader.calls;
    CHECK(controller.step(walk,40000) == 0);
    CHECK(controller.result().error == ActorError::contacts_unsupported);
    CHECK(controller.state() == State::paused && reader.calls == calls);
    CHECK(bytes(controller.snapshot()) == before_contact);
    CHECK(contacts.prepare(config) == Error::ok);
    CHECK(controller.step({},0) == 0);
    CHECK(controller.step(pause,0) == 0);
    CHECK(controller.step({},0) == 0);
    CHECK(controller.step(walk,40000) == 1);
    CHECK(controller.snapshot().movement.ordinal == 4);

    Adapter missing;
    application::MovementController unavailable(movement_test::profile, movement_test::rig(),
                                                reader, missing, spawn, 0);
    CHECK(unavailable.step({},0) == 0);
    const auto missing_before = bytes(unavailable.snapshot());
    CHECK(unavailable.step(walk,40000) == 0);
    CHECK(unavailable.result().error == ActorError::contacts_unavailable);
    CHECK(unavailable.state() == State::paused && bytes(unavailable.snapshot()) == missing_before);
}
} // namespace

int main(int argc, char **argv) {
    if (argc == 2 && std::string(argv[1]) == "vectors") { vectors(); return 0; }
    forbid_allocation = true;
    ownership_and_failures();
    actor_and_controller();
    forbid_allocation = false;
    std::printf("Room contacts: scene=%zu adapter=%zu resident_bound=%zu stack_bound=%zu total=%zu\n",
                sizeof(Scene), sizeof(Adapter), domain::room_contact_resident_bound,
                domain::room_contact_stack_bound,
                domain::room_contact_resident_bound + domain::room_contact_stack_bound);
}
