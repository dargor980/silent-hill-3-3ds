#include "sh3_observer/platform_inventory.hpp"
#include "platform_inventory_vector.hpp"
#include <type_traits>
#ifdef SH3_TEST_NATIVE_HASH
#include "sh3_observer/macos_artifact_manifest.hpp"
#endif
#include "check.hpp"
#include <cstring>
#include <limits>
#include <string>
#include <vector>
using namespace sh3::observer;
namespace {
Sha256 tag(std::uint8_t value) { Sha256 out{};out[0]=value;return out; }
FileObject file(unsigned index) { return {1,10+index,64,3,4,5,6}; }
std::vector<ExpectedFile> config() { return {{"a",64,tag(11)},{"b",64,tag(22)}}; }
struct Birth final : BirthSource {
  int calls{},fail_at{},change_at{};
  bool read(BirthReading& out) noexcept override {++calls;out={7,8,9};if(calls==change_at)++out.seconds;return calls!=fail_at;}
};
struct Nonce final : NonceSource {
  bool fill(ProcessNonce& out) noexcept override {out={};out[0]=1;return true;}
};
struct Files final : ArtifactSource {
  int calls{},fail_at{},change_at{};bool aliases{};
  bool read(std::string_view name,FileDigest& out) noexcept override {
    ++calls;unsigned index=name=="a"?0:1;out={file(aliases?0:index),tag(index==0?11:22)};
    if(calls==change_at)++out.object.inode;return calls!=fail_at;
  }
};
struct Images final : ImageSnapshotSource {
  ImageSnapshot value{};int calls{},fail_at{},change_at{},invalid_at{},address_at{};bool reverse{};
  Images(){value.addresses[0]=0x1000;value.addresses[1]=0x2000;value.addresses[2]=0x8000;value.count=3;value.revision=17;}
  bool read(ImageSnapshot& out) noexcept override {
    ++calls;out=value;if(calls==change_at)++out.revision;
    if(calls==invalid_at)out.revision=0;if(calls==address_at)++out.addresses[0];
    if(reverse && calls%2==0)std::swap(out.addresses[0],out.addresses[1]);return calls!=fail_at;
  }
};
// Deliberately noncryptographic test double. Native tests use CommonCrypto.
struct Hash final : DigestEngine {
  int starts{},updates{},ends{},start_fail{},update_fail{},end_fail{},zero_at{};
  std::uint64_t value{};std::vector<std::vector<std::uint8_t>> frames;
  bool begin() noexcept override {++starts;value=1;frames.emplace_back();return starts!=start_fail;}
  bool update(const void* raw,std::size_t size) noexcept override {
    ++updates;const auto* bytes=static_cast<const std::uint8_t*>(raw);
    frames.back().insert(frames.back().end(),bytes,bytes+size);
    for(std::size_t i=0;i<size;++i)value=value*33+bytes[i];return updates!=update_fail;
  }
  bool finish(Sha256& out) noexcept override {
    ++ends;out={};if(ends!=zero_at)for(unsigned i=0;i<8;++i)out[i]=static_cast<std::uint8_t>(value>>(8*i));return ends!=end_fail;
  }
};

CacheUuid uuid() { CacheUuid out{}; out[0]=9; return out; }
PlatformPolicy policy() { return {IdentityProfile::macos_platform_v1,tag(170),tag(187),tag(204),uuid(),0x2000,0}; }
struct Origins final : ImageOriginSource {
  int calls{},fail_at{},mutate_at{};bool cache_all{},unknown{};std::uint64_t size=4096;
  ImageOriginKind kind{ImageOriginKind::application};
  bool read(std::uintptr_t address,ImageOrigin& out) noexcept override {
    ++calls;out={};
    if(address>=0x8000 || cache_all) {out.kind=ImageOriginKind::platform_cache;out.cache={address,0x1000,0x2000000,uuid()};}
    else {out.kind=kind;out.application={address,size,0,file(address==0x1000?1:0)};}
    if(unknown)out={};
    if(calls==mutate_at) {if(out.kind==ImageOriginKind::platform_cache)out.cache.size+=4096;else out.application.size+=4096;}
    return calls!=fail_at;
  }
};
struct Fixture {
  Birth birth_source;Nonce nonce;Files files;Images images;Origins origins;Hash hash;
  ProcessBirth birth{birth_source,nonce};ManifestGuard manifest{config(),files};
  PlatformInventoryGuard guard{policy(),birth,manifest,images,origins,hash};
  int calls() const {return birth_source.calls+files.calls+images.calls+origins.calls+hash.starts+hash.updates+hash.ends;}
};
using Failure=PlatformInventoryFailure;
void empty(const PlatformInventoryResult& out,Failure why) {
  CHECK(out.failure==why && out.profile==IdentityProfile::unknown && out.scope==IdentityScope::unknown && !out.platform_assumed);
  CHECK(out.process.pid==0 && out.process.birth_ns==0 && out.process.nonce==ProcessNonce{});
  CHECK(out.file_objects==Sha256{} && out.classified_images==Sha256{} && out.policy_evidence==Sha256{});
  CHECK(out.application_evidence==Sha256{} && out.platform_evidence==Sha256{});
  CHECK(out.loader_revision==0 && out.application_images==0 && out.platform_images==0);
}
void terminal(Fixture& f,Failure why) {
  empty(f.guard.sample(),why);const auto calls=f.calls();
  f.birth_source.fail_at=0;f.files.fail_at=0;f.images.fail_at=0;f.origins.fail_at=0;
  f.guard.lose();empty(f.guard.sample(),why);CHECK(f.calls()==calls);
}
std::string hex(const std::vector<std::uint8_t>& bytes) {
  const char* alphabet="0123456789abcdef";std::string out;
  for(auto b:bytes){out.push_back(alphabet[b>>4]);out.push_back(alphabet[b&15]);}return out;
}
void test(const std::string& name) {
  static_assert(!std::is_convertible_v<PlatformInventoryResult,InventoryResult>);
  Fixture f;
  if(name=="stable"||name=="order"||name=="encoding") {
    f.images.reverse=name=="order";const auto r=f.guard.sample();CHECK(r.failure==Failure::none);
    CHECK(r.profile==IdentityProfile::macos_platform_v1 && r.scope==IdentityScope::application_headers && r.platform_assumed);
    CHECK(r.application_images==2 && r.platform_images==1 && r.process.pid==7 && r.loader_revision==17);
    CHECK(r.policy_evidence==tag(170) && r.application_evidence==tag(187) && r.platform_evidence==tag(204));
    CHECK(f.origins.calls==6 && f.files.calls==8 && f.birth_source.calls==4);
    const auto again=f.guard.sample();CHECK(again.failure==Failure::none && again.file_objects==r.file_objects && again.classified_images==r.classified_images);
    CHECK(f.hash.frames[0]==f.hash.frames[2] && f.hash.frames[1]==f.hash.frames[3]);
    if(name=="encoding"){CHECK(hex(f.hash.frames[0])==platform_files_vector);CHECK(hex(f.hash.frames[1])==platform_images_fake_vector);}
  } else if(name=="capacity") {
    f.images.value.count=image_capacity;
    for(std::size_t i=0;i<image_capacity;++i)f.images.value.addresses[i]=0x1000*(i+1);
    const auto r=f.guard.sample();CHECK(r.failure==Failure::none && r.application_images+r.platform_images==image_capacity);
    CHECK(f.origins.calls==2*image_capacity);
  } else if(name=="configuration") {
    for(unsigned i=0;i<9;++i){Fixture x;auto p=policy();
      if(i==0)p.profile=IdentityProfile::unknown;if(i==1)p.profile=static_cast<IdentityProfile>(99);
      if(i==2)p.policy_evidence={};if(i==3)p.application_evidence={};if(i==4)p.platform_evidence={};
      if(i==5)p.expected_cache={};if(i==6)p.main_image=0;if(i==7)p.main_file=artifact_file_capacity;
      PlatformInventoryGuard g(p,x.birth,x.manifest,x.images,x.origins,x.hash);
      if(i==8){p={};CHECK(g.sample().failure==Failure::none);} // Configuration copied, not borrowed.
      else {empty(g.sample(),Failure::policy);CHECK(x.calls()==0);}}
  } else if(name=="main_image") {
    for(unsigned i=0;i<4;++i){Fixture x;auto p=policy();
      if(i==0)p.main_image=0x3000;if(i==1)p.main_file=1;if(i==2)p.main_file=2;if(i==3)x.origins.cache_all=true;
      PlatformInventoryGuard g(p,x.birth,x.manifest,x.images,x.origins,x.hash);
      empty(g.sample(),i==2?Failure::policy:Failure::main_image);
    }
  } else if(name=="unknown") {
    f.origins.unknown=true;terminal(f,Failure::uncovered);
    Fixture x;x.files.aliases=true;terminal(x,Failure::ambiguous);
  } else if(name=="origin_error"||name=="changed_origin") {
    for(int i=1;i<=6;++i){Fixture x;if(name=="origin_error")x.origins.fail_at=i;else x.origins.mutate_at=i;
      terminal(x,name=="origin_error"?Failure::origin:Failure::changed);}
  } else if(name=="invalid_origin"||name=="cache_consistency") {
    struct Bad final : ImageOriginSource {
      Origins source;unsigned mode{};int calls{};
      bool read(std::uintptr_t address,ImageOrigin& out) noexcept override {
        ++calls;source.read(address,out);
        if(address==0x1000){
          if(mode==0)++out.application.address;if(mode==1)out.application.size=0;if(mode==2)out.application.offset=1;
          if(mode==3)out.application.size=UINT64_MAX;if(mode==4)out.application.file.inode=0;
          if(mode==5)out.cache.address=1;if(mode==6)out.kind=static_cast<ImageOriginKind>(99);
          if(mode==7)++out.application.file.inode;
        }
        if(address==0x8000){
          if(mode==8)++out.cache.address;if(mode==9)out.cache.base=0;if(mode==10)out.cache.size=0;
          if(mode==11)out.cache.size=UINT64_MAX;if(mode==12)out.cache.base=0x9000;
          if(mode==13)out.cache.size=0x7000;if(mode==14)out.cache.uuid[0]++;
          if(mode==15)out.application.address=1;
          if(mode==16&&calls>3){out={ImageOriginKind::application,{address,4096,0,file(0)},{}};}
        }
        if(mode==17&&address==0x9000)out.cache.size+=4096;
        return true;
      }
    } bad;
    for(unsigned i=name=="cache_consistency"?16:0;i<(name=="cache_consistency"?18:16);++i){Fixture x;bad={};bad.mode=i;
      if(i==17){x.images.value.addresses[3]=0x9000;x.images.value.count=4;}
      PlatformInventoryGuard g(policy(),x.birth,x.manifest,x.images,bad,x.hash);
      empty(g.sample(),i==7?Failure::uncovered:i>=16?Failure::changed:Failure::invalid);
      const auto calls=bad.calls;empty(g.sample(),i==7?Failure::uncovered:i>=16?Failure::changed:Failure::invalid);CHECK(calls==bad.calls);
    }
  } else if(name=="birth_error"||name=="birth_changed") {
    for(int i=1;i<=4;++i){Fixture x;if(name=="birth_error")x.birth_source.fail_at=i;else x.birth_source.change_at=i;terminal(x,Failure::birth);}
  } else if(name=="loader_error") {
    for(int i=1;i<=2;++i){Fixture x;x.images.fail_at=i;terminal(x,Failure::loader);}
  } else if(name=="invalid_inventory") {
    for(int i=0;i<7;++i){Fixture x;
      if(i==0)x.images.value.count=0;if(i==1)x.images.value.count=image_capacity+1;
      if(i==2)x.images.value.addresses[0]=0;if(i==3)x.images.value.addresses[1]=0x1000;
      if(i==4)x.images.value.revision=0;if(i==5)x.images.value.revision=UINT64_MAX;if(i==6)x.images.invalid_at=2;
      terminal(x,Failure::invalid);}
  } else if(name=="manifest_error"||name=="manifest_changed") {
    for(int i=1;i<=8;++i){Fixture x;if(name=="manifest_error")x.files.fail_at=i;else x.files.change_at=i;terminal(x,Failure::manifest);}
  } else if(name=="manifest_policy") {
    struct Large final : ArtifactSource {
      std::uint64_t size{};
      bool read(std::string_view name,FileDigest& out) noexcept override {out={file(name=="a"?0:1),tag(11)};out.object.size=size;return true;}
    } large;
    for(unsigned i=0;i<2;++i){Fixture x;large.size=i==0?artifact_file_limit+1:artifact_file_limit;
      std::vector<ExpectedFile> expected{{"a",large.size,tag(11)},{"b",large.size,tag(11)}};
      if(i==1)expected.push_back({"c",large.size,tag(11)});
      ManifestGuard manifest(expected,large,ArtifactDomain::system_cache);
      PlatformInventoryGuard g(policy(),x.birth,manifest,x.images,x.origins,x.hash);empty(g.sample(),Failure::policy);
    }
  } else if(name=="ambiguous") {
    f.files.aliases=true;terminal(f,Failure::ambiguous);CHECK(f.origins.calls==0);
  } else if(name=="loader_changed") {
    for(unsigned i=0;i<3;++i){Fixture x;
      if(i==0)x.images.change_at=2;if(i==1)x.images.address_at=2;
      if(i==2){CHECK(x.guard.sample().failure==Failure::none);x.images.value.count=2;}
      terminal(x,Failure::changed);}
  } else if(name=="baseline") {
    CHECK(f.guard.sample().failure==Failure::none);++f.origins.size;terminal(f,Failure::changed);
    Fixture x;CHECK(x.guard.sample().failure==Failure::none);x.images.value.revision+=2;terminal(x,Failure::changed);
  } else if(name=="digest_error"||name=="digest_zero") {
    CHECK(f.guard.sample().failure==Failure::none);
    if(name=="digest_zero"){for(int i=1;i<=2;++i){Fixture x;x.hash.zero_at=i;terminal(x,Failure::digest);}}
    else {
      for(int i=1;i<=2;++i){Fixture x;x.hash.start_fail=i;terminal(x,Failure::digest);}
      for(int i=1;i<=f.hash.updates;++i){Fixture x;x.hash.update_fail=i;terminal(x,Failure::digest);}
      for(int i=1;i<=2;++i){Fixture x;x.hash.end_fail=i;terminal(x,Failure::digest);}
    }
  } else if(name=="lost") {
    for(unsigned i=0;i<2;++i){Fixture x;if(i)CHECK(x.guard.sample().failure==Failure::none);const auto calls=x.calls();x.guard.lose();terminal(x,Failure::lost);CHECK(x.calls()==calls);}
  } else if(name=="evidence_domains") {
    const auto first=f.guard.sample();CHECK(first.failure==Failure::none);
    for(unsigned i=0;i<3;++i){Fixture x;auto p=policy();
      if(i==0)p.policy_evidence[0]++;if(i==1)p.application_evidence[0]++;if(i==2)p.platform_evidence[0]++;
      PlatformInventoryGuard g(p,x.birth,x.manifest,x.images,x.origins,x.hash);const auto r=g.sample();
      CHECK(r.failure==Failure::none && r.file_objects!=first.file_objects && r.classified_images!=first.classified_images);
    }
#ifdef SH3_TEST_NATIVE_HASH
  } else if(name=="native_hash") {
    MacOSSha256 hash;PlatformInventoryGuard g(policy(),f.birth,f.manifest,f.images,f.origins,hash);const auto r=g.sample();
    CHECK(r.failure==Failure::none && hex({r.file_objects.begin(),r.file_objects.end()})==platform_files_sha256);
    CHECK(hex({r.classified_images.begin(),r.classified_images.end()})==platform_images_sha256);
#endif
  } else CHECK(false);
}
}
int main(int argc,char** argv){CHECK(argc==2);test(argv[1]);}
