#include "sh3_observer/image_identity.hpp"
#include <limits>

namespace sh3::observer {
bool same_file(const FileObject& a, const FileObject& b) noexcept {
  return a.device == b.device && a.inode == b.inode && a.size == b.size &&
    a.modified_seconds == b.modified_seconds && a.changed_seconds == b.changed_seconds &&
    a.modified_ns == b.modified_ns && a.changed_ns == b.changed_ns;
}
bool valid_file(const FileObject& f) noexcept {
  return f.device != 0 && f.inode != 0 && f.size != 0 &&
    f.modified_seconds >= 0 && f.changed_seconds >= 0 &&
    f.modified_ns < 1000000000 && f.changed_ns < 1000000000;
}
namespace {
bool same_mapping(const MappedFile& a, const MappedFile& b) noexcept {
  return a.address == b.address && a.size == b.size && a.offset == b.offset && same_file(a.file, b.file);
}
bool valid_mapping(const MappedFile& m, std::uintptr_t header) noexcept {
  return header != 0 && m.address == header && m.size != 0 && m.offset == 0 &&
    m.address <= std::numeric_limits<std::uint64_t>::max() - m.size && valid_file(m.file);
}
}
BindingResult ImageBinding::fail(ImageFailure reason) noexcept {
  if (failure_ == ImageFailure::none) failure_ = reason;
  baseline_ = {};
  return {{}, failure_};
}
void ImageBinding::lose() noexcept { (void)fail(ImageFailure::lost); }
BindingResult ImageBinding::sample() noexcept {
  if (failure_ != ImageFailure::none) return {{}, failure_};
  FileObject first{}, last{};
  MappedFile before{}, after{};
  if (!file_.read(first) || !mapping_.read(header_, before) ||
      !file_.read(last) || !mapping_.read(header_, after)) return fail(ImageFailure::unavailable);
  if (!valid_file(first) || !valid_file(last) || !valid_mapping(before, header_) ||
      !valid_mapping(after, header_)) return fail(ImageFailure::invalid);
  if (!same_file(first, last) || !same_file(first, before.file) ||
      !same_mapping(before, after) || (ready_ && !same_mapping(baseline_, before)))
    return fail(ImageFailure::changed);
  baseline_ = before;
  ready_ = true;
  return {baseline_, ImageFailure::none};
}
ImageLedger::ImageLedger(std::uint64_t initial_revision) noexcept {
  state_.revision = initial_revision;
  failed_ = initial_revision == 0 || initial_revision == std::numeric_limits<std::uint64_t>::max();
}
bool ImageLedger::advance() noexcept {
  if (failed_ || state_.revision >= std::numeric_limits<std::uint64_t>::max() - 1) {
    failed_ = true;
    return false;
  }
  ++state_.revision;
  return true;
}
void ImageLedger::add(std::uintptr_t address) noexcept {
  if (failed_) return;
  if (address == 0 || state_.count == image_capacity) { failed_ = true; return; }
  for (std::size_t i = 0; i < state_.count; ++i)
    if (state_.addresses[i] == address) { failed_ = true; return; }
  if (advance()) state_.addresses[state_.count++] = address;
}
void ImageLedger::remove(std::uintptr_t address) noexcept {
  if (failed_) return;
  for (std::size_t i = 0; i < state_.count; ++i) {
    if (state_.addresses[i] == address) {
      if (!advance()) return;
      for (std::size_t j = i + 1; j < state_.count; ++j) state_.addresses[j - 1] = state_.addresses[j];
      state_.addresses[--state_.count] = 0;
      return;
    }
  }
  failed_ = true;
}
bool ImageLedger::read(ImageSnapshot& output) const noexcept {
  output = {};
  if (failed_) return false;
  output = state_;
  return true;
}
} // namespace sh3::observer
