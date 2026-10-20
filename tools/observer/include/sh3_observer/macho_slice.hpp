#pragma once
#include "sh3_observer/artifact_manifest.hpp"

namespace sh3::observer {
inline constexpr std::size_t macho_slice_capacity = 32;
enum class SliceFormat : std::uint8_t { unknown, thin, fat32, fat64 };
struct SliceRequest { std::uint32_t cpu{}, subtype{}; std::uint64_t offset{}; };
struct MachSlice {
  SliceFormat format{SliceFormat::unknown};
  std::uint64_t offset{}, size{};
  std::array<std::uint8_t,32> header{};
};
struct SliceBinding { MappedFile mapping{}; MachSlice slice{}; };
enum class SliceFailure { none, invalid, unsupported, unavailable, ambiguous, missing, changed, identity, header };
bool same_slice(const MachSlice&, const MachSlice&) noexcept;
bool valid_slice_binding(const SliceBinding&) noexcept;
SliceFailure select_macho_slice(ByteSource&, std::uint64_t file_size, SliceRequest, MachSlice&) noexcept;
SliceFailure bind_macho_slice(const MappedFile&, FileIdentitySource&, ByteSource& file,
                             ByteSource& resident, SliceBinding&) noexcept;
class SliceBindingSource {
public:
  virtual ~SliceBindingSource() = default;
  virtual bool read(std::uintptr_t, SliceBinding&) noexcept = 0;
};
} // namespace sh3::observer
