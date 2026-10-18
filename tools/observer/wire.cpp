#include "sh3_observer/wire.hpp"
#include <algorithm>
namespace sh3::observer {
namespace {
std::uint32_t read32(const std::uint8_t* p) noexcept {
  std::uint32_t value{};
  for (unsigned i = 0; i < 4; ++i) value |= std::uint32_t{p[i]} << (8 * i);
  return value;
}
void put(std::vector<std::uint8_t>& out, std::uint64_t value, unsigned bytes) {
  for (unsigned i = 0; i < bytes; ++i) out.push_back(static_cast<std::uint8_t>(value >> (8 * i)));
}
void snapshot(std::vector<std::uint8_t>& out, const Snapshot& s) {
  put(out, s.pid, 8); put(out, s.pc, 4); put(out, s.cycle, 8);
  put(out, s.ee_main, 8); put(out, s.vmap, 8); put(out, s.exposed_ram, 4);
  put(out, s.flags, 4); put(out, s.game_crc, 4); put(out, s.page_count, 4);
  for (const auto& page : s.pages) {
    put(out, page.number, 4); put(out, 0, 4); put(out, page.bias, 8);
  }
  put(out, 0, 4);
}
} // namespace
bool decode_request(const std::uint8_t* bytes, std::size_t size, Request& out) noexcept {
  if (!bytes || size != request_bytes || bytes[0] != 0xe0 || bytes[1] != 1 ||
      bytes[2] || bytes[3]) return false;
  Request r{};
  std::copy(bytes + 4, bytes + 20, r.session.begin());
  r.sequence = read32(bytes + 20); r.expected_pc = read32(bytes + 24);
  r.virtual_start = read32(bytes + 28); r.size = read32(bytes + 32);
  r.expected_offset = read32(bytes + 36);
  out = r;
  return true;
}
std::vector<std::uint8_t> encode_reply(const Result& input) {
  // Rejected captures must never leak partially acquired addresses or bytes.
  const auto safe = input.status == Status::ok && !valid_request(input.request)
    ? failure(input.request, Status::request) : input;
  const bool ok = safe.status == Status::ok;
  const auto& r = safe.request;
  std::vector<std::uint8_t> out{'S', 'H', '3', 'O', 1, static_cast<std::uint8_t>(safe.status), 0, 0};
  out.reserve(reply_header_bytes + (ok ? r.size : 0));
  out.insert(out.end(), r.session.begin(), r.session.end());
  for (auto value : {r.sequence, r.expected_pc, r.virtual_start, r.size, r.expected_offset,
                    ok ? r.size : 0, ok ? safe.offset : 0, ok && safe.matches ? 1U : 0U})
    put(out, value, 4);
  snapshot(out, ok ? safe.before : Snapshot{});
  snapshot(out, ok ? safe.after : Snapshot{});
  if (ok) out.insert(out.end(), safe.data.begin(), safe.data.begin() + r.size);
  return out;
}
} // namespace sh3::observer
