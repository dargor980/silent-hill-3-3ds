#pragma once

namespace sh3::observer::pcsx2 {
struct RuntimeVMShutdownRequest {
  bool allow_confirm{}, allow_save_to_state{}, default_save_to_state{};
};
enum class RuntimeServiceUIAction { none, exit_application, shutdown_vm };

// UI-thread-only policy. Does not cancel, join, dispatch or depend on Qt.
class RuntimeUIIntent final {
public:
  void start() noexcept { active_=true; }
  bool active() const noexcept { return active_; }
  bool request_vm(RuntimeVMShutdownRequest request) noexcept {
    if (!active_) return false;
    if (!explicit_exit_ && !vm_) { request_=request;vm_=true; }
    return true;
  }
  bool request_exit() noexcept {
    if (!active_) return false;
    explicit_exit_=true;vm_=false;
    return true;
  }
  // Owner must first prove cleanup complete and join IO.
  RuntimeServiceUIAction consume(RuntimeVMShutdownRequest& request) noexcept {
    request={};
    if (!active_) return RuntimeServiceUIAction::none;
    active_=false;
    if (vm_) { request=request_;return RuntimeServiceUIAction::shutdown_vm; }
    return RuntimeServiceUIAction::exit_application;
  }
private:
  RuntimeVMShutdownRequest request_{};
  bool active_{}, explicit_exit_{}, vm_{};
};
}
