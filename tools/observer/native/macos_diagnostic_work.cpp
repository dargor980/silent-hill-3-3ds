#include "sh3_observer/macos_diagnostic_work.hpp"
#include "sh3_observer/macos_artifact_manifest.hpp"
#include "sh3_observer/macos_image_identity.hpp"
#include "sh3_observer/macos_launch_files.hpp"
#include "sh3_observer/macos_page_binding.hpp"
#include "sh3_observer/macos_platform_origin.hpp"
#include "sh3_observer/macos_process_birth.hpp"
#include "sh3_observer/macos_slice_binding.hpp"
#include <utility>

namespace sh3::observer {
namespace {
using Reason = DiagnosticRejection;
class Control final : public InspectionControl {
public:
  Control(DiagnosticBudget& budget, InspectionControl* local) : budget_(budget), local_(local) {}
  bool checkpoint(InspectionStep step) noexcept override {
    if (stopped_ || !budget_.checkpoint() || !inspect_continue(local_,step) || !budget_.checkpoint()) {
      stopped_ = true; return false;
    }
    return true;
  }
private:
  DiagnosticBudget& budget_;
  InspectionControl* local_;
  bool stopped_{};
};
class ConfigSource final : public FileIdentitySource, public ByteSource {
public:
  ConfigSource(const std::string& path, Control& control) : control_(control), file_(path) {}
  bool read(FileObject& out) noexcept override {
    out = {};
    if (!control_.checkpoint(InspectionStep::file_identity) || !file_.read(out) ||
        !control_.checkpoint(InspectionStep::file_identity)) { out = {}; return false; }
    return true;
  }
  bool read_at(std::uint64_t at, void* bytes, std::size_t n, std::size_t& got) noexcept override {
    got = 0;
    if (!control_.checkpoint(InspectionStep::file_read) || !file_.read_at(at,bytes,n,got) ||
        !control_.checkpoint(InspectionStep::file_read)) { got = 0; return false; }
    return true;
  }
  bool close() noexcept { return file_.close(); }
private:
  Control& control_;
  MacOSPageAnchor file_;
};
class Events final : public ImageSnapshotSource {
public:
  explicit Events(Control& control) : control_(control) {}
  bool read(ImageSnapshot& out) noexcept override {
    out = {};
    if (!control_.checkpoint(InspectionStep::images) || !MacOSImageEvents::read(out) ||
        !control_.checkpoint(InspectionStep::images)) { out = {}; return false; }
    return true;
  }
private:
  Control& control_;
};
struct Inventory final {
  MacOSLaunchFiles files;
  ManifestGuard manifest;
  MacOSBirthSource source;
  MacOSNonceSource nonce;
  ProcessBirth birth;
  Events events;
  MacOSSliceMappings slices;
  MacOSPlatformOrigins origins;
  MacOSSha256 hash;
  PlatformInventoryGuard guard;
  Inventory(const LaunchManifest& m, const MacOSDiagnosticConfiguration& c, Control& control)
    : files(m,&control), manifest(launch_expected_files(m),files), birth(source,nonce), events(control),
      origins(events,slices,macos_cache_calls(),&control), hash(&control),
      guard({c.expectation.profile,m.policy_evidence,c.expectation.application_evidence,m.platform_evidence,
             m.cache,c.main_image,m.main_file},birth,manifest,events,origins,hash) {}
};
class Work final : public DiagnosticWork {
public:
  Work(MacOSDiagnosticConfiguration config, DiagnosticBudget& budget, InspectionControl* local,
       MacOSDiagnosticDetails* details)
    : config_(std::move(config)), control_(budget,local), details_(details) { if(details_) *details_={}; }
  Reason prepare(DiagnosticBudget&) override {
    if (closed_ || attempted_) return fail(Reason::protocol);
    attempted_ = true;
    if (!valid_diagnostic_expectation(config_.expectation) || !config_.main_image ||
        config_.manifest_path.empty() || config_.manifest_path[0] != '/' ||
        config_.manifest_path.find('\0') != std::string::npos) return fail(Reason::configuration);
    if (!control_.checkpoint(InspectionStep::preparation)) return fail(Reason::unavailable);
    LaunchManifest manifest;
    {
      source_ = std::make_unique<ConfigSource>(config_.manifest_path,control_);
      MacOSSha256 hash(&control_);
      if (!control_.checkpoint(InspectionStep::preparation)) return fail(Reason::unavailable);
      const auto result=read_launch_manifest(*source_,*source_,hash,config_.expectation.application_evidence,manifest);
      if(details_) details_->manifest=result;
      if(result != LaunchFailure::none) return fail(Reason::configuration);
    }
    if (manifest.policy_evidence != config_.expectation.policy_evidence ||
        manifest.platform_evidence != config_.expectation.platform_evidence) return fail(Reason::configuration);
    if (!control_.checkpoint(InspectionStep::preparation)) return fail(Reason::unavailable);
    inventory_ = std::make_unique<Inventory>(manifest,config_,control_);
    if(details_) details_->origins=inventory_->origins.failure();
    if (!control_.checkpoint(InspectionStep::preparation)) return fail(Reason::unavailable);
    if (inventory_->origins.failure() != PlatformOriginFailure::none) return fail(Reason::inventory);
    if(details_) details_->prepared=true;
    return Reason::none;
  }
  Reason sample(DiagnosticBudget&, DiagnosticObservation& out) override {
    out = {};
    if (failure_ != Reason::none) return failure_;
    if (closed_ || !inventory_) return fail(Reason::protocol);
    if (!control_.checkpoint(InspectionStep::preparation)) return fail(Reason::unavailable);
    const auto result = inventory_->guard.sample();
    if(details_) { details_->sampled=true; details_->inventory=result.failure; details_->origins=inventory_->origins.failure(); }
    if (!control_.checkpoint(InspectionStep::preparation)) return fail(Reason::unavailable);
    if (result.failure != PlatformInventoryFailure::none) return fail(Reason::inventory);
    out.inventory = result; // No runtime guard binding: facts and epochs stay unknown/zero.
    return Reason::none;
  }
  bool close() noexcept override {
    if (inventory_ && !inventory_->files.close()) close_ok_ = false;
    inventory_.reset();
    if (source_ && !source_->close()) close_ok_ = false;
    source_.reset(); closed_ = true;
    if(details_) details_->closed=close_ok_;
    return close_ok_;
  }
private:
  Reason fail(Reason reason) noexcept { if (failure_ == Reason::none) failure_ = reason; return failure_; }
  const MacOSDiagnosticConfiguration config_;
  Control control_;
  MacOSDiagnosticDetails* details_;
  std::unique_ptr<ConfigSource> source_;
  std::unique_ptr<Inventory> inventory_;
  Reason failure_{Reason::none};
  bool attempted_{}, closed_{}, close_ok_{true};
};
}
MacOSDiagnosticWorkFactory::MacOSDiagnosticWorkFactory(MacOSDiagnosticConfiguration config, InspectionControl* local,
                                                     MacOSDiagnosticDetails* details)
  : configuration_(std::move(config)), local_control_(local), details_(details) {}
std::unique_ptr<DiagnosticWork> MacOSDiagnosticWorkFactory::create(DiagnosticBudget& budget) {
  return std::make_unique<Work>(configuration_,budget,local_control_,details_);
}
} // namespace sh3::observer
