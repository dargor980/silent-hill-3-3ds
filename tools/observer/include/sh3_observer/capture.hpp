#pragma once

#include <array>
#include <cstddef>
#include <cstdint>

namespace sh3::observer {
constexpr std::uint32_t page_size = 4096;
constexpr std::uint32_t ram_size = 32 * 1024 * 1024;
constexpr std::uint64_t sign_bit = std::uint64_t{1} << 63;

enum class Status : std::uint8_t {
  ok, request, pause, save_pending, anchors, pc, handler, outside_ram,
  noncontiguous, unstable, read, content, timeout
};
struct Request {
  std::array<std::uint8_t, 16> session{};
  std::uint32_t sequence{}, expected_pc{}, virtual_start{}, size{}, expected_offset{};
};
struct Page {
  std::uint32_t number{};
  std::uint64_t bias{};
};
struct Snapshot {
  std::uint64_t pid{};
  std::uint32_t pc{};
  std::uint64_t cycle{};
  std::uint64_t ee_main{}, vmap{};
  std::uint32_t exposed_ram{}, flags{}, game_crc{}, page_count{};
  std::array<Page, 2> pages{};
};
struct Result {
  Request request{};
  Status status{Status::request};
  std::uint32_t offset{};
  bool matches{};
  Snapshot before{}, after{};
  std::array<std::uint8_t, page_size> data{};
};
// Adapter returns value snapshots and copies only a validated EE RAM offset.
// Implementations must not throw or retain the caller's buffers.
class Reader {
public:
  virtual ~Reader() = default;
  virtual Snapshot snapshot(const Request&) noexcept = 0;
  virtual bool read_ram(std::uint32_t offset, std::uint32_t size,
                        std::uint8_t* output) noexcept = 0;
};
bool valid_request(const Request&) noexcept;
bool same_snapshot(const Snapshot&, const Snapshot&) noexcept;
Result failure(const Request&, Status) noexcept;
Result capture(const Request&, Reader&) noexcept;
} // namespace sh3::observer
