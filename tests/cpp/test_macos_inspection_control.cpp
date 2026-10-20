#include "sh3_observer/macos_artifact_manifest.hpp"
#include "sh3_observer/macos_launch_files.hpp"
#include "sh3_observer/macos_page_binding.hpp"
#include "sh3_observer/macos_diagnostic_work.hpp"
#include "sh3_observer/macos_image_identity.hpp"
#include "launch_manifest_fixture.hpp"
#include "check.hpp"
#include <atomic>
#include <filesystem>
#include <fstream>
#include <mach-o/dyld.h>
#include <sys/stat.h>
#include <thread>
#include <unistd.h>

using namespace sh3::observer;
using namespace std::chrono_literals;
namespace fs = std::filesystem;
namespace {
struct Control final : InspectionControl {
  std::array<unsigned,7> counts{};
  InspectionStep target{};
  unsigned cut{};
  bool checkpoint(InspectionStep step) noexcept override {
    const auto n = ++counts[static_cast<unsigned>(step)];
    return step != target || n != cut;
  }
};
Sha256 digest(const std::string& data) {
  MacOSSha256 hash; Sha256 out; CHECK(hash.begin());
  for(std::size_t offset=0;offset<data.size();offset+=digest_block_size)
    CHECK(hash.update(data.data()+offset,std::min(digest_block_size,data.size()-offset)));
  CHECK(hash.finish(out)); return out;
}
void write(const fs::path& p, const std::string& data) {
  std::ofstream out(p,std::ios::binary);out<<data;CHECK(out.good());
}
std::vector<int> held(const fs::path& p) {
  struct stat expected{};CHECK(stat(p.c_str(),&expected)==0);
  std::vector<int> fds;
  for(int fd=0;fd<1024;++fd) {
    struct stat s{};
    if(fstat(fd,&s)==0 && s.st_dev==expected.st_dev && s.st_ino==expected.st_ino)fds.push_back(fd);
  }
  return fds;
}
void empty(const FileDigest& out) { CHECK(out.object.inode==0 && out.sha256==Sha256{}); }
struct Clock final : DiagnosticClock {
  std::atomic<std::int64_t> ns{10000000000LL};
  DiagnosticClock::Clock::time_point now() noexcept override {return DiagnosticClock::Clock::time_point(std::chrono::nanoseconds(ns.load()));}
};
struct Expire final : InspectionControl {
  Clock& clock; InspectionStep target; bool done{};
  Expire(Clock& c,InspectionStep t):clock(c),target(t){}
  bool checkpoint(InspectionStep step) noexcept override {
    if(!done && step==target){done=true;clock.ns+=5000000000LL;}
    return true;
  }
};
}
int main(int argc,char** argv) {
  CHECK(argc==3);const std::string mode=argv[1];fs::create_directories(argv[2]);
  std::string name=(fs::path(argv[2])/"control-XXXXXX").string();CHECK(mkdtemp(name.data()));const fs::path root(name);
  const std::string data(digest_block_size*2+137,'x');write(root/"data",data);
  const std::vector<ExpectedFile> expected{{"data",data.size(),digest(data)}};
  auto m=launch_fixture::manifest();m.roots={root.string()};m.files={{0,expected[0]}};m.main_file=0;
  const auto encoded=launch_fixture::encode(m);const std::string raw(encoded.begin(),encoded.end());write(root/"manifest",raw);
  if(mode=="hash") {
    for(unsigned cut=1;cut<=6;++cut) {
      Control control;control.target=InspectionStep::digest;control.cut=cut;MacOSSha256 hash(&control);Sha256 out;out.fill(7);
      const bool ok=hash.begin() && hash.update("x",1) && hash.finish(out);CHECK(!ok);
      control.cut=0;CHECK(!hash.begin() && !hash.update("x",1) && !hash.finish(out) && out==Sha256{});
    }
  } else if(mode=="open" || mode=="identity" || mode=="read" || mode=="digest" || mode=="preparation") {
    const auto target=mode=="open"?InspectionStep::file_open:mode=="identity"?InspectionStep::file_identity:
      mode=="read"?InspectionStep::file_read:mode=="digest"?InspectionStep::digest:InspectionStep::preparation;
    Control baseline;FileDigest out;
    {MacOSArtifactFiles files(root.string(),expected,baseline);CHECK(files.read("data",out));CHECK(files.close());}
    const auto count=baseline.counts[static_cast<unsigned>(target)];CHECK(count>=2);
    for(unsigned cut=1;cut<=count;++cut) {
      Control c;c.target=target;c.cut=cut;
      MacOSArtifactFiles files(root.string(),expected,c);out.object.inode=99;out.sha256.fill(7);
      CHECK(!files.read("data",out));empty(out);c.cut=0;
      CHECK(!files.read("data",out));empty(out);CHECK(files.close() && files.close());
      CHECK(held(root/"data").empty() && held(root).empty());
    }
  } else if(mode=="launch") {
    for(unsigned cut=1;cut<=4;++cut) {
      Control c;c.target=InspectionStep::preparation;c.cut=cut;MacOSLaunchFiles files(m,&c);FileDigest out;
      CHECK(!files.read("0/data",out));empty(out);c.cut=0;CHECK(!files.read("0/data",out));
      CHECK(files.close() && held(root/"data").empty() && held(root).empty());
    }
  } else if(mode=="close") {
    MacOSArtifactFiles files(root.string(),expected);FileDigest out;
    CHECK(files.read("data",out) && held(root/"data").size()==1);
    CHECK(files.close() && files.close() && held(root/"data").empty());CHECK(!files.read("data",out));empty(out);
    MacOSLaunchFiles launch(m);CHECK(launch.read("0/data",out));CHECK(launch.close() && launch.close());
    CHECK(held(root).empty() && held(root/"data").empty());CHECK(!launch.read("0/data",out));
    MacOSPageAnchor anchor((root/"data").string());FileObject object;CHECK(anchor.read(object));
    CHECK(anchor.close() && anchor.close() && held(root/"data").empty());CHECK(!anchor.read(object) && object.inode==0);
  } else if(mode=="close_failure") {
    {MacOSArtifactFiles files(root.string(),expected);auto fds=held(root/"data");CHECK(fds.size()==1);CHECK(::close(fds[0])==0);
      CHECK(!files.close() && !files.close());}
    {MacOSLaunchFiles files(m);auto fds=held(root/"data");CHECK(fds.size()==1);CHECK(::close(fds[0])==0);
      CHECK(!files.close() && !files.close());}
    {MacOSPageAnchor anchor((root/"data").string());auto fds=held(root/"data");CHECK(fds.size()==1);CHECK(::close(fds[0])==0);
      CHECK(!anchor.close() && !anchor.close());}
    CHECK(held(root/"data").empty() && held(root).empty());
  } else if(mode=="factory" || mode=="deadline" || mode=="missing" || mode=="evidence") {
    ImageSnapshot initial;CHECK(MacOSImageEvents::read(initial));
    MacOSDiagnosticConfiguration config{(root/"manifest").string(),
      {IdentityProfile::macos_platform_slices_v2,m.policy_evidence,digest(raw),m.platform_evidence},
      reinterpret_cast<std::uintptr_t>(_dyld_get_image_header(0))};
    for(const auto step:{InspectionStep::preparation,InspectionStep::file_read,InspectionStep::digest,InspectionStep::file_open,InspectionStep::origin}) {
      auto c=config;Clock clock;Expire expire(clock,step);InspectionControl* control=mode=="deadline"?&expire:nullptr;
      if(mode=="factory") c.main_image=0;
      if(mode=="missing") c.manifest_path=(root/"absent").string();
      if(mode=="evidence") c.expectation.policy_evidence[0]^=1;
      MacOSDiagnosticDetails details;
      DiagnosticWorker worker(c.expectation,std::make_unique<MacOSDiagnosticWorkFactory>(c,control,&details),clock);
      DiagnosticRequest request;request.challenge.fill(1);request.sequence=1;CHECK(worker.submit(request,{}));
      CHECK(worker.wait_stopped_until(DiagnosticClock::Clock::now()+4s));
      CHECK(worker.status().reason==(mode=="deadline"?DiagnosticRejection::deadline:DiagnosticRejection::configuration));
      DiagnosticCompletion out;CHECK(!worker.take(out));CHECK(held(root/"data").empty() && held(root/"manifest").empty() && held(root).empty());
      CHECK(details.closed);
      if(mode=="deadline")CHECK(expire.done);
      if(mode=="missing")CHECK(details.manifest==LaunchFailure::identity);
      if(mode=="evidence")CHECK(details.manifest==LaunchFailure::none && !details.prepared);
    }
  } else CHECK(false);
}
