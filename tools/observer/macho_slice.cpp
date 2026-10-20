#include "sh3_observer/macho_slice.hpp"
#include <algorithm>

namespace sh3::observer {
namespace {
using Header = std::array<std::uint8_t,32>;
std::uint32_t le32(const std::uint8_t* p) noexcept {
  return std::uint32_t(p[0]) | std::uint32_t(p[1])<<8 | std::uint32_t(p[2])<<16 | std::uint32_t(p[3])<<24;
}
std::uint32_t be32(const std::uint8_t* p) noexcept {
  return std::uint32_t(p[3]) | std::uint32_t(p[2])<<8 | std::uint32_t(p[1])<<16 | std::uint32_t(p[0])<<24;
}
std::uint64_t be64(const std::uint8_t* p) noexcept { return std::uint64_t(be32(p))<<32 | be32(p+4); }
bool cpu64(std::uint32_t cpu) noexcept { return cpu == 0x1000007 || cpu == 0x100000c; }
bool header_valid(const Header& h, std::uint64_t size) noexcept {
  const auto type=le32(h.data()+12), commands=le32(h.data()+16), bytes=le32(h.data()+20);
  return size >= h.size() && le32(h.data()) == 0xfeedfacf && cpu64(le32(h.data()+4)) &&
    (type == 2 || type == 6 || type == 8) && commands && bytes <= 1024*1024 &&
    commands <= bytes/8 && bytes <= size-h.size() && !le32(h.data()+28);
}
bool exact(ByteSource& source, std::uint64_t offset, void* data, std::size_t size) noexcept {
  std::size_t got{}; return source.read_at(offset,data,size,got) && got == size;
}
struct Catalog {
  std::array<MachSlice,macho_slice_capacity> slices{};
  std::array<std::uint32_t,macho_slice_capacity> alignments{};
  std::size_t count{};
};
SliceFailure catalog(ByteSource& source, std::uint64_t file_size, Catalog& out) noexcept {
  std::array<std::uint8_t,8> prefix{};
  if (!exact(source,0,prefix.data(),prefix.size())) return SliceFailure::unavailable;
  const auto magic=be32(prefix.data()); std::size_t stride{};
  SliceFormat format{};
  if (magic == 0xcffaedfe) { format=SliceFormat::thin; out.count=1; }
  else if (magic == 0xcafebabe || magic == 0xcafebabf) {
    format=magic == 0xcafebabe ? SliceFormat::fat32 : SliceFormat::fat64;
    stride=format == SliceFormat::fat32 ? 20 : 32; out.count=be32(prefix.data()+4);
    if (!out.count || out.count > macho_slice_capacity) return SliceFailure::invalid;
  } else return SliceFailure::unsupported;
  std::array<std::uint8_t,macho_slice_capacity*32> table{};
  const auto table_size=out.count*stride, table_end=8+table_size;
  if (stride && (table_end > file_size || !exact(source,8,table.data(),table_size))) return SliceFailure::unavailable;
  for (std::size_t i=0;i<out.count;++i) {
    auto& s=out.slices[i]; s.format=format; const auto p=table.data()+i*stride;
    if (!stride) { s.offset=0; s.size=file_size; }
    else {
      s.offset=stride == 20 ? be32(p+8) : be64(p+8);
      s.size=stride == 20 ? be32(p+12) : be64(p+16);
      const auto align=be32(p+(stride == 20 ? 16 : 24)); out.alignments[i]=align;
      if (align > 63 || (stride == 32 && be32(p+28)) || s.offset < table_end ||
          s.offset%(std::uint64_t(1)<<align)) return SliceFailure::invalid;
    }
    if (s.size < s.header.size() || s.offset > file_size || s.size > file_size-s.offset) return SliceFailure::invalid;
    if (!exact(source,s.offset,s.header.data(),s.header.size())) return SliceFailure::unavailable;
    if (!header_valid(s.header,s.size)) return SliceFailure::invalid;
    if (stride && (le32(s.header.data()+4) != be32(p) || le32(s.header.data()+8) != be32(p+4))) return SliceFailure::invalid;
    for (std::size_t j=0;j<i;++j) {
      const auto& other=out.slices[j];
      if (le32(other.header.data()+4) == le32(s.header.data()+4) && le32(other.header.data()+8) == le32(s.header.data()+8)) return SliceFailure::ambiguous;
      if (s.offset < other.offset+other.size && other.offset < s.offset+s.size) return SliceFailure::invalid;
    }
  }
  return SliceFailure::none;
}
}
bool same_slice(const MachSlice& a, const MachSlice& b) noexcept {
  return a.format == b.format && a.offset == b.offset && a.size == b.size && a.header == b.header;
}
bool valid_slice_binding(const SliceBinding& b) noexcept {
  const auto& m=b.mapping; const auto& s=b.slice;
  if (!m.address || m.size < 32 || m.size > UINT64_MAX-m.address || !valid_file(m.file) ||
      m.file.size > artifact_file_limit || s.offset != m.offset || s.offset > m.file.size || s.size > m.file.size-s.offset ||
      !header_valid(s.header,s.size)) return false;
  if (s.format == SliceFormat::thin) return !s.offset && s.size == m.file.size;
  if (s.format == SliceFormat::fat32) return s.offset >= 28;
  if (s.format == SliceFormat::fat64) return s.offset >= 40;
  return false;
}
SliceFailure select_macho_slice(ByteSource& source, std::uint64_t file_size, SliceRequest wanted, MachSlice& out) noexcept {
  out={};
  if (file_size < 32 || file_size > artifact_file_limit || wanted.offset > file_size) return SliceFailure::invalid;
  if (!cpu64(wanted.cpu)) return SliceFailure::unsupported;
  Catalog first{},last{}; auto status=catalog(source,file_size,first);
  if (status != SliceFailure::none) return status;
  status=catalog(source,file_size,last); if (status != SliceFailure::none) return status;
  if (first.count != last.count || first.alignments != last.alignments) return SliceFailure::changed;
  const MachSlice* selected=nullptr;
  for (std::size_t i=0;i<first.count;++i) {
    const auto& s=first.slices[i];
    if (!same_slice(s,last.slices[i])) return SliceFailure::changed;
    if (le32(s.header.data()+4) == wanted.cpu && le32(s.header.data()+8) == wanted.subtype && s.offset == wanted.offset) selected=&s;
  }
  if (!selected) return SliceFailure::missing;
  out=*selected; return SliceFailure::none;
}
SliceFailure bind_macho_slice(const MappedFile& mapping, FileIdentitySource& identity,
    ByteSource& file, ByteSource& resident, SliceBinding& out) noexcept {
  out={};
  if (!mapping.address || mapping.size < 32 || mapping.size > UINT64_MAX-mapping.address ||
      !valid_file(mapping.file) || mapping.file.size > artifact_file_limit || mapping.file.size < 32 ||
      mapping.offset > mapping.file.size-32) return SliceFailure::invalid;
  FileObject before{},after{};
  if (!identity.read(before) || !same_file(before,mapping.file)) return SliceFailure::identity;
  Header first{},last{};
  if (!exact(resident,0,first.data(),first.size())) return SliceFailure::unavailable;
  MachSlice slice{};
  const auto status=select_macho_slice(file,before.size,{le32(first.data()+4),le32(first.data()+8),mapping.offset},slice);
  if (status != SliceFailure::none) return status;
  if (first != slice.header) return SliceFailure::header;
  if (!exact(resident,0,last.data(),last.size())) return SliceFailure::unavailable;
  if (first != last) return SliceFailure::changed;
  if (!identity.read(after) || !same_file(before,after)) return SliceFailure::identity;
  SliceBinding result{mapping,slice};
  if (!valid_slice_binding(result)) return SliceFailure::invalid;
  out=result; return SliceFailure::none;
}
} // namespace sh3::observer
