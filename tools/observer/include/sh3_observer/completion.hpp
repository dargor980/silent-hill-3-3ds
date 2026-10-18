#pragma once
#include "sh3_observer/capture.hpp"
#include <chrono>
#include <condition_variable>
#include <mutex>

namespace sh3::observer {
// Own via shared_ptr in both producer and queued callback. No borrowed stack data.
class Completion final {
public:
  explicit Completion(Request request) : request_(request) {}
  void run(Reader& reader) noexcept {
    {
      std::lock_guard<std::mutex> lock(mutex_);
      if (cancelled_ || started_) return;
      started_ = true;
    }
    auto result = capture(request_, reader);
    {
      std::lock_guard<std::mutex> lock(mutex_);
      if (cancelled_) return;
      result_ = result;
      ready_ = true;
    }
    cv_.notify_one();
  }
  Result wait(std::chrono::milliseconds timeout) {
    std::unique_lock<std::mutex> lock(mutex_);
    if (!cv_.wait_for(lock, timeout, [this] { return ready_; })) {
      cancelled_ = true;
      return failure(request_, Status::timeout);
    }
    return result_;
  }
private:
  Request request_;
  Result result_{};
  std::mutex mutex_;
  std::condition_variable cv_;
  bool started_{}, ready_{}, cancelled_{};
};
} // namespace sh3::observer
