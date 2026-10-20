#pragma once
#include "sh3_observer/diagnostic_worker.hpp"
#include "sh3_observer/inspection_control.hpp"
#include "sh3_observer/launch_manifest.hpp"
#include "sh3_observer/macos_platform_origin.hpp"
#include <string>

namespace sh3::observer {
struct MacOSDiagnosticConfiguration {
  std::string manifest_path;
  DiagnosticExpectation expectation{};
  std::uintptr_t main_image{};
};
// Optional local telemetry. Only the worker writes; read after joining it.
struct MacOSDiagnosticDetails {
  LaunchFailure manifest{LaunchFailure::none};
  PlatformOriginFailure origins{PlatformOriginFailure::none};
  PlatformInventoryFailure inventory{PlatformInventoryFailure::none};
  bool prepared{}, sampled{}, closed{};
};
// Launcher configuration only. Initialize MacOSImageEvents before submitting.
// Optional local test control is borrowed, single worker, never remote-selected.
class MacOSDiagnosticWorkFactory final : public DiagnosticWorkFactory {
public:
  explicit MacOSDiagnosticWorkFactory(MacOSDiagnosticConfiguration,
                                     InspectionControl* local_control = nullptr,
                                     MacOSDiagnosticDetails* details = nullptr);
  std::unique_ptr<DiagnosticWork> create(DiagnosticBudget&) override;
private:
  const MacOSDiagnosticConfiguration configuration_;
  InspectionControl* const local_control_;
  MacOSDiagnosticDetails* const details_;
};
} // namespace sh3::observer
