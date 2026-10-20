#pragma once
#include <array>
#include <cstddef>
#include <cstdint>

namespace sh3::observer {
struct FileObject {
  std::uint64_t device{}, inode{}, size{};
  std::int64_t modified_seconds{}, changed_seconds{};
  std::uint32_t modified_ns{}, changed_ns{};
};
bool same_file(const FileObject&, const FileObject&) noexcept;
bool valid_file(const FileObject&) noexcept;
struct MappedFile {
  std::uint64_t address{}, size{}, offset{};
  FileObject file{};
};
class FileIdentitySource {
public:
  virtual ~FileIdentitySource() = default;
  virtual bool read(FileObject&) noexcept = 0;
};
class MappingSource {
public:
  virtual ~MappingSource() = default;
  virtual bool read(std::uintptr_t, MappedFile&) noexcept = 0;
};
enum class ImageFailure { none, unavailable, invalid, changed, lost };
struct BindingResult {
  MappedFile mapping{};
  ImageFailure failure{ImageFailure::none};
};
class ImageBinding final {
public:
  ImageBinding(std::uintptr_t header, FileIdentitySource& file, MappingSource& mapping) noexcept
    : header_(header), file_(file), mapping_(mapping) {}
  ImageBinding(const ImageBinding&) = delete;
  ImageBinding& operator=(const ImageBinding&) = delete;
  BindingResult sample() noexcept;
  void lose() noexcept;
private:
  BindingResult fail(ImageFailure) noexcept;
  std::uintptr_t header_;
  FileIdentitySource& file_;
  MappingSource& mapping_;
  MappedFile baseline_{};
  ImageFailure failure_{ImageFailure::none};
  bool ready_{};
};

inline constexpr std::size_t image_capacity = 2048;
struct ImageSnapshot {
  std::array<std::uintptr_t, image_capacity> addresses{};
  std::size_t count{};
  std::uint64_t revision{};
};
// Serialized by the owner. No OS calls, allocation, or image dereference.
class ImageLedger final {
public:
  explicit ImageLedger(std::uint64_t initial_revision = 1) noexcept;
  void add(std::uintptr_t) noexcept;
  void remove(std::uintptr_t) noexcept;
  bool read(ImageSnapshot&) const noexcept;
private:
  bool advance() noexcept;
  ImageSnapshot state_{};
  bool failed_{};
};
} // namespace sh3::observer
