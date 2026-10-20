#pragma once
#include "runtime_ui_intent.hpp"

namespace sh3::observer::pcsx2 {
enum class RuntimeServiceStart { disabled, started, failed };
// UI owner only; local launcher configuration is copied before IO starts.
RuntimeServiceStart start_runtime_service() noexcept;
// CPU notification only. Does not dispatch, allocate, block or acquire a scope.
void notify_runtime_service_paused() noexcept;
// Any thread may request cancellation. CPU must remain alive during cleanup.
void cancel_runtime_service() noexcept;
// UI owner only. Claims an exit only if this service started successfully.
// Signals cancellation; the existing UI timer must keep pumping until finished,
// return through the join epilogue, and only then stop CPU. Never joins here.
bool cancel_runtime_service_from_ui() noexcept;
// UI only: defer the native shutdown flow until diagnostic IO has joined.
// This cancels diagnostics, not the VM; consent is obtained by the native dialog.
bool defer_runtime_vm_shutdown(RuntimeVMShutdownRequest) noexcept;
// Consumes the intent once, only after cleanup and join. none means pending or
// inactive. UI must stop its timer before dispatching the returned native action.
RuntimeServiceUIAction poll_runtime_service_ui(RuntimeVMShutdownRequest&) noexcept;
bool runtime_service_finished() noexcept;
// UI owner only. Never waits for running IO; joins only after IO reports done.
// Retain the service and keep CPU alive while this returns false.
bool finish_runtime_service() noexcept;
}
