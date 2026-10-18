#include "sh3_observer/capture.hpp"
#include <algorithm>

namespace sh3::observer {
bool valid_request(const Request& r) noexcept {
  return std::any_of(r.session.begin(), r.session.end(), [](auto b) { return b != 0; }) &&
    r.sequence >= 1 && r.sequence <= 256 && r.expected_pc % 4 == 0 &&
    r.size >= 1 && r.size <= page_size &&
    std::uint64_t{r.virtual_start} + r.size <= (std::uint64_t{1} << 32) &&
    r.expected_offset <= ram_size - r.size;
}
bool same_snapshot(const Snapshot& a, const Snapshot& b) noexcept {
  if (a.pid != b.pid || a.pc != b.pc || a.cycle != b.cycle ||
      a.ee_main != b.ee_main || a.vmap != b.vmap || a.exposed_ram != b.exposed_ram ||
      a.flags != b.flags || a.game_crc != b.game_crc || a.page_count != b.page_count)
    return false;
  for (std::size_t i = 0; i < a.pages.size(); ++i)
    if (a.pages[i].number != b.pages[i].number || a.pages[i].bias != b.pages[i].bias)
      return false;
  return true;
}
Result failure(const Request& request, Status status) noexcept {
  Result result{};
  result.request = request;
  result.status = status;
  return result;
}
namespace {
Status resolve(const Request& r, const Snapshot& s, std::uint32_t& first) noexcept {
  if (!(s.flags & 1)) return Status::pause;
  if (s.flags & 2) return Status::save_pending;
  if (s.flags != 1 || !s.pid || s.ee_main < page_size ||
      s.ee_main > sign_bit - ram_size || s.ee_main % page_size ||
      s.vmap < 8 || s.vmap > sign_bit - (std::uint64_t{1} << 23) ||
      s.vmap % 8 || s.exposed_ram != ram_size) return Status::anchors;
  if (s.pc != r.expected_pc) return Status::pc;
  const auto end = std::uint64_t{r.virtual_start} + r.size;
  const auto start_page = r.virtual_start / page_size;
  const auto count = (end - 1) / page_size - start_page + 1;
  if (s.page_count != count) return Status::anchors;
  for (std::size_t i = 0; i < s.pages.size(); ++i) {
    const auto& entry = s.pages[i];
    if (i >= count) {
      if (entry.number || entry.bias) return Status::anchors;
      continue;
    }
    if (entry.number != start_page + i) return Status::anchors;
    const auto start = std::max(std::uint64_t{r.virtual_start}, std::uint64_t{entry.number} * page_size);
    const auto stop = std::min(end, (std::uint64_t{entry.number} + 1) * page_size);
    const auto pointer = entry.bias + start; // unsigned wrap is the vtlb convention
    if (pointer & sign_bit) return Status::handler;
    if (pointer < s.ee_main || pointer - s.ee_main > ram_size - (stop - start))
      return Status::outside_ram;
    const auto offset = static_cast<std::uint32_t>(pointer - s.ee_main);
    if (i == 0) first = offset;
    if (offset != first + start - r.virtual_start) return Status::noncontiguous;
  }
  return Status::ok;
}
} // namespace
Result capture(const Request& r, Reader& reader) noexcept {
  if (!valid_request(r)) return failure(r, Status::request);
  Result result{};
  result.request = r;
  result.before = reader.snapshot(r);
  auto status = resolve(r, result.before, result.offset);
  if (status != Status::ok) return failure(r, status);
  std::array<std::uint8_t, page_size> second{};
  if (!reader.read_ram(result.offset, r.size, result.data.data()) ||
      !reader.read_ram(result.offset, r.size, second.data())) return failure(r, Status::read);
  result.after = reader.snapshot(r);
  std::uint32_t after_offset{};
  status = resolve(r, result.after, after_offset);
  if (status != Status::ok) return failure(r, status);
  if (!same_snapshot(result.before, result.after)) return failure(r, Status::unstable);
  if (!std::equal(result.data.begin(), result.data.begin() + r.size, second.begin()))
    return failure(r, Status::content);
  result.status = Status::ok;
  result.matches = result.offset == r.expected_offset;
  return result;
}
} // namespace sh3::observer
