#pragma once

namespace sh3::observer {
// Thread-confined, lexical scopes only. The owner outlives all its scopes.
// This proves a CPU control-flow boundary, never global writer exclusion.
class CpuBoundary final {
public:
  class Activity final {
  public:
    ~Activity();
    Activity(const Activity&) = delete;
    Activity& operator=(const Activity&) = delete;
  private:
    friend class CpuBoundary;
    explicit Activity(CpuBoundary&) noexcept;
    CpuBoundary& owner_;
    const bool was_busy_;
  };
  class Boundary final {
  public:
    ~Boundary();
    Boundary(const Boundary&) = delete;
    Boundary& operator=(const Boundary&) = delete;
    bool valid() const noexcept { return valid_; }
  private:
    friend class CpuBoundary;
    explicit Boundary(CpuBoundary&) noexcept;
    CpuBoundary& owner_;
    bool valid_{};
  };
  CpuBoundary() = default;
  CpuBoundary(const CpuBoundary&) = delete;
  CpuBoundary& operator=(const CpuBoundary&) = delete;
  void set_online(bool online) noexcept;
  bool at_boundary() const noexcept { return boundary_ && boundary_->valid_; }
  Activity activity() noexcept { return Activity(*this); }
  Boundary enter() noexcept { return Boundary(*this); }
private:
  void invalidate() noexcept;
  bool online_{}, busy_{};
  Boundary* boundary_{};
};
} // namespace sh3::observer
