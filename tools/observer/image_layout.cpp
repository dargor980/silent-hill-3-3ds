#include "sh3_observer/image_layout.hpp"
#include <algorithm>
#include <cstring>
#include <limits>
#include <memory>
#include <new>

namespace sh3::observer {
namespace {
using Byte = unsigned char;
std::uint32_t u32(const Byte* p) noexcept {
  return std::uint32_t(p[0]) | std::uint32_t(p[1]) << 8 | std::uint32_t(p[2]) << 16 | std::uint32_t(p[3]) << 24;
}
std::uint64_t u64(const Byte* p) noexcept { return u32(p) | std::uint64_t(u32(p + 4)) << 32; }
LayoutFailure header(const Byte* bytes, std::size_t size, ImageLayout& out) noexcept {
  if (!bytes || size < 32) return LayoutFailure::invalid;
  if (u32(bytes) != 0xfeedfacf) return LayoutFailure::unsupported;
  out.cpu = u32(bytes + 4); out.subtype = u32(bytes + 8); out.type = u32(bytes + 12);
  out.commands = u32(bytes + 16); out.command_bytes = u32(bytes + 20); out.flags = u32(bytes + 24);
  if ((out.cpu != 0x01000007 && out.cpu != 0x0100000c) ||
      (out.type != 2 && out.type != 6 && out.type != 7 && out.type != 8)) return LayoutFailure::unsupported;
  if (u32(bytes + 28) != 0 || out.commands == 0 || out.commands > 4096 ||
      out.command_bytes > layout_command_limit || out.command_bytes % 8 != 0 ||
      out.command_bytes < out.commands * 8) return LayoutFailure::invalid;
  return LayoutFailure::none;
}
bool name(const Byte* bytes, std::array<char, 16>& out) noexcept {
  bool end = false;
  for (std::size_t i = 0; i < out.size(); ++i) {
    const auto b = bytes[i];
    if (b == 0) end = true;
    else if (end || b < 32 || b > 126) return false;
    out[i] = static_cast<char>(b);
  }
  return out[0] != 0;
}
bool exact(ByteSource& source, Byte* bytes, std::size_t size) noexcept {
  for (std::size_t offset = 0; offset < size;) {
    const auto wanted = std::min(digest_block_size, size - offset);
    std::size_t got{};
    if (!source.read_at(offset, bytes + offset, wanted, got) || got != wanted) return false;
    offset += got;
  }
  return true;
}
}
LayoutFailure parse_image_layout(const void* data, std::size_t size, ImageLayout& out) noexcept {
  out = {};
  const auto* bytes = static_cast<const Byte*>(data);
  ImageLayout value{};
  const auto status = header(bytes, size, value);
  if (status != LayoutFailure::none) return status;
  if (size != 32 + value.command_bytes) return LayoutFailure::invalid;
  std::size_t offset = 32, text_count = 0;
  for (std::uint32_t i = 0; i < value.commands; ++i) {
    if (size - offset < 8) return LayoutFailure::invalid;
    const auto* command = bytes + offset;
    const auto kind = u32(command), length = u32(command + 4);
    if (length < 8 || length % 8 != 0 || length > size - offset) return LayoutFailure::invalid;
    if (kind == 1) return LayoutFailure::unsupported; // LC_SEGMENT is not a 64-bit segment.
    if (kind == 0x19) {
      if (length < 72 || value.count == layout_segment_capacity) return LayoutFailure::invalid;
      ImageSegment segment{};
      if (!name(command + 8, segment.name)) return LayoutFailure::invalid;
      segment.address = u64(command + 24); segment.size = u64(command + 32);
      segment.file_offset = u64(command + 40); segment.file_size = u64(command + 48);
      segment.maximum_protection = u32(command + 56); segment.initial_protection = u32(command + 60);
      segment.sections = u32(command + 64); segment.flags = u32(command + 68);
      if (length != 72 + std::uint64_t(segment.sections) * 80 || segment.file_size > segment.size ||
          segment.size > std::numeric_limits<std::uint64_t>::max() - segment.address ||
          segment.file_size > std::numeric_limits<std::uint64_t>::max() - segment.file_offset ||
          segment.maximum_protection > 7 || segment.initial_protection > 7 ||
          (segment.initial_protection & ~segment.maximum_protection) != 0) return LayoutFailure::invalid;
      for (std::size_t j = 0; j < value.count; ++j) {
        const auto& previous = value.segments[j];
        if (segment.size != 0 && previous.size != 0 && segment.address < previous.address + previous.size &&
            previous.address < segment.address + segment.size) return LayoutFailure::invalid;
      }
      if (segment.name == std::array<char, 16>{'_', '_', 'T', 'E', 'X', 'T'}) {
        if (++text_count != 1 || segment.file_size < size || !(segment.initial_protection & 1)) return LayoutFailure::invalid;
        value.header_address = segment.address;
      }
      value.segments[value.count++] = segment;
    }
    offset += length;
  }
  if (offset != size || text_count != 1) return LayoutFailure::invalid;
  out = value;
  return LayoutFailure::none;
}
LayoutFailure read_image_layout(ByteSource& source, ImageLayout& out) noexcept {
  out = {};
  std::array<Byte, 32> first{};
  if (!exact(source, first.data(), first.size())) return LayoutFailure::unavailable;
  ImageLayout initial{};
  const auto status = header(first.data(), first.size(), initial);
  if (status != LayoutFailure::none) return status;
  const auto size = 32 + initial.command_bytes;
  std::unique_ptr<Byte[]> a(new (std::nothrow) Byte[size]), b(new (std::nothrow) Byte[size]);
  if (!a || !b || !exact(source, a.get(), size) || !exact(source, b.get(), size)) return LayoutFailure::unavailable;
  if (std::memcmp(first.data(), a.get(), first.size()) != 0 || std::memcmp(a.get(), b.get(), size) != 0) return LayoutFailure::changed;
  return parse_image_layout(a.get(), size, out);
}
} // namespace sh3::observer
