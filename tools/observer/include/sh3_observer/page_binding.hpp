#pragma once
#include "sh3_observer/image_identity.hpp"

namespace sh3::observer {
struct PageReading {
  std::uint64_t object{}, offset{};
  bool resident{}, external{}, modified{};
};
struct PageFileReading { FileObject file{}; PageReading page{}; };
class PageSource {
public:
  virtual ~PageSource() = default;
  virtual bool read(std::uintptr_t, PageReading&) noexcept = 0;
};
class PageFileSource {
public:
  virtual ~PageFileSource() = default;
  virtual bool read(PageFileReading&) noexcept = 0;
};
enum class PageFailure { none, invalid, unavailable, mismatch, changed, lost };
struct PageBindingResult {
  FileObject file{};
  std::uint64_t object{}, offset{};
  PageFailure failure{PageFailure::none};
};
// Trusted provider ports only; evidence covers the queried byte's backing page.
class PageBinding final {
public:
  PageBinding(std::uintptr_t address, PageFileSource& file, PageSource& pages) noexcept
    : address_(address), file_(file), pages_(pages) {}
  PageBinding(const PageBinding&) = delete;
  PageBinding& operator=(const PageBinding&) = delete;
  PageBindingResult sample() noexcept;
  void lose() noexcept;
private:
  PageBindingResult fail(PageFailure) noexcept;
  std::uintptr_t address_;
  PageFileSource& file_;
  PageSource& pages_;
  PageBindingResult baseline_{};
  PageFailure failure_{PageFailure::none};
  bool ready_{};
};
} // namespace sh3::observer
