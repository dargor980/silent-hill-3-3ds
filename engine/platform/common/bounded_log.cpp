#include "sh3/platform/bounded_log.hpp"

namespace sh3::platform {
void BoundedLog::record(domain::SessionState state) noexcept {
    entries_[next_] = state;
    next_ = (next_ + 1) % capacity;
    if (size_ < capacity) {
        ++size_;
    }
}

std::size_t BoundedLog::size() const noexcept { return size_; }

std::optional<domain::SessionState> BoundedLog::at(std::size_t index) const noexcept {
    if (index >= size_) {
        return std::nullopt;
    }
    const auto oldest = size_ == capacity ? next_ : 0;
    return entries_[(oldest + index) % capacity];
}
} // namespace sh3::platform
