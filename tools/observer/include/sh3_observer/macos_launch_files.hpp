#pragma once
#include "sh3_observer/launch_manifest.hpp"
#include "sh3_observer/inspection_control.hpp"
#include <memory>

namespace sh3::observer {
class MacOSLaunchFiles final : public ArtifactSource {
public:
  explicit MacOSLaunchFiles(const LaunchManifest&, InspectionControl* = nullptr);
  ~MacOSLaunchFiles() override;
  MacOSLaunchFiles(const MacOSLaunchFiles&)=delete;
  MacOSLaunchFiles& operator=(const MacOSLaunchFiles&)=delete;
  bool read(std::string_view,FileDigest&) noexcept override;
  bool close() noexcept;
private:
  struct Impl;
  std::unique_ptr<Impl> impl_;
};
} // namespace sh3::observer
