#include "sh3_observer/macos_launch_files.hpp"
#include "sh3_observer/macos_artifact_manifest.hpp"
#include <unistd.h>

namespace sh3::observer {
struct MacOSLaunchFiles::Impl {
  InspectionControl* control;
  const LaunchManifest manifest;
  const int owner{getpid()};
  std::vector<ExpectedFile> expected;
  std::vector<std::unique_ptr<MacOSArtifactFiles>> roots;
  bool failed{}, close_ok{true};
  explicit Impl(const LaunchManifest& m, InspectionControl* c):control(c),manifest(m),expected(launch_expected_files(m)) {
    if(!check() || expected.empty() || owner<=0){failed=true;return;}
    for(std::size_t i=0;i<manifest.roots.size();++i) {
      if(!check())return;
      std::vector<ExpectedFile> files;
      for(const auto& f:manifest.files)if(f.root==i)files.push_back(f.file);
      roots.push_back(std::make_unique<MacOSArtifactFiles>(manifest.roots[i],files,::pread,control));
    }
  }
  bool check() noexcept {
    if(failed || !inspect_continue(control,InspectionStep::preparation)){failed=true;return false;}
    return true;
  }
};
MacOSLaunchFiles::MacOSLaunchFiles(const LaunchManifest& m, InspectionControl* c):impl_(std::make_unique<Impl>(m,c)) {}
MacOSLaunchFiles::~MacOSLaunchFiles(){(void)close();}
bool MacOSLaunchFiles::close() noexcept {
  impl_->failed=true;
  for(const auto& root:impl_->roots)if(!root->close())impl_->close_ok=false;
  return impl_->close_ok;
}
bool MacOSLaunchFiles::read(std::string_view name,FileDigest& out) noexcept {
  out={};
  if(!impl_->check())return false;
  if(getpid()!=impl_->owner){impl_->failed=true;return false;}
  for(std::size_t i=0;i<impl_->expected.size();++i) {
    if(name!=impl_->expected[i].name)continue;
    const auto& f=impl_->manifest.files[i];
    if(impl_->roots[f.root]->read(f.file.name,out) && impl_->check())return true;
    out={};impl_->failed=true;return false;
  }
  impl_->failed=true;return false;
}
} // namespace sh3::observer
