#include "check.hpp"
#include "sh3_observer/capture.hpp"
#include "sh3_observer/completion.hpp"
#include "sh3_observer/wire.hpp"
#include <algorithm>
#include <chrono>
#include <functional>
#include <iostream>
#include <memory>
#include <thread>
#include <vector>
using namespace sh3::observer;
using namespace std::chrono_literals;

Request request() { return {{{1}}, 1, 0x100000, 0x1ff0, 32, 0xff0}; }
Snapshot sample(const Request& r) {
  Snapshot s{42, r.expected_pc, 0x10000004dULL, 0x10000000, 0x20000000, ram_size, 1, 0x44556677, 0, {}};
  const auto end = std::uint64_t{r.virtual_start} + r.size;
  s.page_count = static_cast<std::uint32_t>((end - 1) / page_size - r.virtual_start / page_size + 1);
  for (unsigned i = 0; i < s.page_count; ++i)
    s.pages[i] = {r.virtual_start / page_size + i, s.ee_main + r.expected_offset - r.virtual_start};
  return s;
}
struct Fake : Reader {
  Snapshot a, b;
  unsigned snapshots{}, reads{}, fail_read{};
  bool change_content{};
  explicit Fake(const Request& r) : a(sample(r)), b(a) {}
  Snapshot snapshot(const Request&) noexcept override { return snapshots++ == 0 ? a : b; }
  bool read_ram(std::uint32_t offset, std::uint32_t size, std::uint8_t* output) noexcept override {
    ++reads;
    for (unsigned i = 0; i < size; ++i) output[i] = static_cast<std::uint8_t>((offset + i) ^ 0x5a);
    if (change_content && reads == 2) output[size - 1] ^= 1;
    return reads != fail_read;
  }
};
void rejected(Request r, const std::function<void(Snapshot&)>& mutate, Status status) {
  Fake f(r); mutate(f.a); f.b = f.a;
  const auto result = capture(r, f);
  CHECK(result.status == status);
  CHECK(f.reads == 0);
  CHECK(result.before.pid == 0 && result.offset == 0);
}
void domain() {
  auto r = request();
  Fake f(r); auto result = capture(r, f);
  CHECK(result.status == Status::ok && result.matches && result.offset == 0xff0);
  CHECK(f.reads == 2 && f.snapshots == 2);
  Fake alias(r); r.expected_offset += 32;
  result = capture(r, alias);
  CHECK(result.status == Status::ok && !result.matches && result.offset == 0xff0);
  r = request();
  const std::vector<std::function<void(Request&)>> invalid{
    [](auto& q) {q.session = {};}, [](auto& q) {q.sequence = 0;},
    [](auto& q) {q.sequence = 257;}, [](auto& q) {q.expected_pc++;},
    [](auto& q) {q.size = 0;}, [](auto& q) {q.size = 4097;},
    [](auto& q) {q.virtual_start = 0xffffffff;},
    [](auto& q) {q.expected_offset = ram_size;}
  };
  for (auto mutate : invalid) {
    auto q = r; mutate(q); Fake reader(r);
    CHECK(!valid_request(q)); CHECK(capture(q, reader).status == Status::request);
    CHECK(reader.snapshots == 0);
  }
  rejected(r, [](auto& s) {s.flags = 0;}, Status::pause);
  rejected(r, [](auto& s) {s.flags = 3;}, Status::save_pending);
  rejected(r, [](auto& s) {s.pc += 4;}, Status::pc);
  const std::vector<std::function<void(Snapshot&)>> anchors{
    [](auto& s) {s.flags = 5;}, [](auto& s) {s.pid = 0;},
    [](auto& s) {s.ee_main = 0;}, [](auto& s) {s.ee_main = sign_bit;},
    [](auto& s) {s.ee_main++;}, [](auto& s) {s.vmap = 0;},
    [](auto& s) {s.vmap = sign_bit;}, [](auto& s) {s.vmap++;},
    [](auto& s) {s.exposed_ram++;}, [](auto& s) {s.page_count = 0;},
    [](auto& s) {s.page_count = 3;}, [](auto& s) {s.pages[0].number++;},
    [](auto& s) {s.pages[1].number--;}
  };
  for (auto mutate : anchors) rejected(r, mutate, Status::anchors);
  rejected(r, [](auto& s) {s.pages[0].bias = sign_bit;}, Status::handler);
  rejected(r, [](auto& s) {s.pages[0].bias = 0;}, Status::outside_ram);
  rejected(r, [](auto& s) {s.pages[1].bias += ram_size;}, Status::outside_ram);
  rejected(r, [](auto& s) {s.pages[1].bias++;}, Status::noncontiguous);
  for (const auto& mutate : std::vector<std::function<void(Snapshot&)>>{[](auto& s) {s.pid++;},
       [](auto& s) {s.cycle++;}, [](auto& s) {s.game_crc++;},
       [](auto& s) {s.vmap += 8;}, [](auto& s) {s.ee_main += page_size;
           for (auto& p : s.pages) p.bias += page_size;},
       [](auto& s) {for (auto& p : s.pages) p.bias += page_size;}}) {
    Fake reader(r); mutate(reader.b);
    CHECK(capture(r, reader).status == Status::unstable);
  }
  for (auto mutate : anchors) {
    Fake reader(r); mutate(reader.b); CHECK(capture(r, reader).status == Status::anchors);
  }
  for (unsigned fail : {1U, 2U}) {
    Fake reader(r); reader.fail_read = fail; CHECK(capture(r, reader).status == Status::read);
  }
  Fake changing(r); changing.change_content = true;
  CHECK(capture(r, changing).status == Status::content);
  Fake resumed(r); resumed.b.flags = 0; CHECK(capture(r, resumed).status == Status::pause);
  r.size = 1; r.sequence = 256;
  rejected(r, [](auto& s) {s.pages[1].number = 1;}, Status::anchors);
  rejected(r, [](auto& s) {s.pages[1].bias = 1;}, Status::anchors);
  // Independent arithmetic oracle for every page boundary, high addresses and wrapped biases.
  for (const auto base : {0U, 0x20000000U, 0xffffe000U}) {
    for (unsigned i = 0; i < page_size; ++i) {
      Request q{{{1}}, 256, 0xfffffffcU, base + i, 1 + i, ram_size - 1 - i};
      Fake reader(q); const auto value = capture(q, reader);
      CHECK(value.status == Status::ok && value.offset == ram_size - 1 - i && value.matches);
      for (unsigned j = 0; j < q.size; ++j)
        CHECK(value.data[j] == static_cast<std::uint8_t>((q.expected_offset + j) ^ 0x5a));
    }
  }
  Request last{{{1}}, 1, 0, 0xffffffffU, 1, ram_size - 1};
  Fake last_reader(last);
  CHECK(capture(last, last_reader).status == Status::ok);
  auto a = sample(r), b = a;
  for (const auto& mutate : std::vector<std::function<void(Snapshot&)>>{[](auto& s) {s.pc++;},
       [](auto& s) {s.exposed_ram++;}, [](auto& s) {s.flags++;},
       [](auto& s) {s.page_count++;}, [](auto& s) {s.pages[0].number++;}}) {
    b = a; mutate(b); CHECK(!same_snapshot(a, b));
  }
}
void wire() {
  auto r = request();
  std::array<std::uint8_t, 40> packet{};
  packet[0] = 0xe0; packet[1] = 1; packet[4] = 1; packet[20] = 1;
  packet[26] = 0x10; packet[28] = 0xf0; packet[29] = 0x1f;
  packet[32] = 32; packet[36] = 0xf0; packet[37] = 0xf;
  Request parsed{};
  CHECK(decode_request(packet.data(), packet.size(), parsed));
  CHECK(parsed.virtual_start == r.virtual_start && parsed.expected_pc == r.expected_pc);
  CHECK(parsed.size == r.size && parsed.expected_offset == r.expected_offset);
  CHECK(parsed.session == r.session && parsed.sequence == r.sequence);
  CHECK(!decode_request(nullptr, 40, parsed));
  for (unsigned size = 0; size < 40; ++size) CHECK(!decode_request(packet.data(), size, parsed));
  CHECK(!decode_request(packet.data(), 41, parsed));
  for (unsigned index = 0; index < 4; ++index) {
    auto bad = packet; bad[index]++; CHECK(!decode_request(bad.data(), 40, parsed));
  }
  Fake reader(r); auto result = capture(r, reader);
  CHECK(encode_reply(result).size() == 232 + r.size);
  auto alias = result; alias.matches = false;
  CHECK(encode_reply(alias)[52] == 0);
  for (unsigned code = 1; code <= 12; ++code) {
    result.status = static_cast<Status>(code);
    const auto out = encode_reply(result);
    CHECK(out.size() == 232 && out[5] == code);
    CHECK(std::all_of(out.begin() + 44, out.end(), [](auto b) {return b == 0;}));
  }
  result.status = Status::ok; result.request.size = 4097;
  CHECK(encode_reply(result)[5] == static_cast<unsigned>(Status::request));
}
struct Blocking : Fake {
  using Fake::Fake;
  std::mutex mutex;
  std::condition_variable cv;
  bool entered{}, released{};
  Snapshot snapshot(const Request& r) noexcept override {
    std::unique_lock<std::mutex> lock(mutex);
    entered = true; cv.notify_one(); cv.wait(lock, [this] {return released;});
    return Fake::snapshot(r);
  }
};
void completion() {
  auto r = request();
  Fake reader(r);
  auto queued = std::make_shared<Completion>(r);
  auto late = queued;
  CHECK(queued->wait(0ms).status == Status::timeout);
  queued.reset(); late->run(reader); CHECK(reader.reads == 0);
  Completion ready(r); ready.run(reader); ready.run(reader);
  CHECK(ready.wait(0ms).status == Status::ok && reader.reads == 2);
  auto active = std::make_shared<Completion>(r);
  Blocking blocked(r);
  std::thread worker([active, &blocked] {active->run(blocked);});
  {
    std::unique_lock<std::mutex> lock(blocked.mutex);
    CHECK(blocked.cv.wait_for(lock, 2s, [&blocked] {return blocked.entered;}));
  }
  CHECK(active->wait(0ms).status == Status::timeout);
  active.reset();
  { std::lock_guard<std::mutex> lock(blocked.mutex); blocked.released = true; }
  blocked.cv.notify_one(); worker.join();
  Completion concurrent(r); Fake normal(r);
  std::thread successful([&] {concurrent.run(normal);});
  CHECK(concurrent.wait(2s).status == Status::ok); successful.join();
}
int main(int argc, char**) {
  if (argc == 2) {
    auto r = request(); Fake reader(r);
    const auto bytes = encode_reply(capture(r, reader));
    for (auto b : bytes) std::printf("%02x", b);
    std::puts(""); return 0;
  }
  domain(); wire(); completion();
  std::puts("observer: domain, wire, cancellation passed");
}
