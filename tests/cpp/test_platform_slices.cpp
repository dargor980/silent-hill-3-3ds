#include "sh3_observer/platform_inventory.hpp"
#include "macho_slice_fixture.hpp"
#include "check.hpp"
#ifdef SH3_TEST_NATIVE_HASH
#include "sh3_observer/macos_artifact_manifest.hpp"
#include "platform_slices_vector.hpp"
#endif
#include <string>
#include <vector>
using namespace sh3::observer;
namespace {
using Failure=PlatformInventoryFailure;
Sha256 tag(unsigned n){Sha256 s{};s[0]=n;return s;}
FileObject file(){return {1,2,8256,3,4,5,6};}
struct Birth final:BirthSource{bool read(BirthReading& b)noexcept override{b={7,8,9};return true;}};
struct Nonce final:NonceSource{bool fill(ProcessNonce& n)noexcept override{n={};n[0]=1;return true;}};
struct Files final:ArtifactSource{bool read(std::string_view,FileDigest& d)noexcept override{d={file(),tag(11)};return true;}};
struct Images final:ImageSnapshotSource{bool read(ImageSnapshot& s)noexcept override{s={};s.count=2;s.revision=17;s.addresses[0]=0x1000;s.addresses[1]=0x8000;return true;}};
CacheUuid uuid(){CacheUuid u{};u[0]=9;return u;}
PlatformPolicy policy(){return {IdentityProfile::macos_platform_slices_v2,tag(170),tag(187),tag(204),uuid(),0x1000,0};}
struct Origins final:ImageOriginSource{
  ImageOrigin application{},cache{};int calls{},mutate_at{},field{};
  Origins(){slice_fixture::Source bytes(slice_fixture::fat());MachSlice s{};CHECK(select_macho_slice(bytes,bytes.bytes.size(),{0x1000007,3,4096},s)==SliceFailure::none);
    application={ImageOriginKind::application,{0x1000,4096,4096,file()},{},s};cache={ImageOriginKind::platform_cache,{}, {0x8000,0x1000,0x2000000,uuid()},{}};}
  static void mutate(ImageOrigin& o,int field){
    if(field==0)o.slice.header[24]^=1;
    if(field==1)o.slice.size--;
    if(field==2)o.slice.format=SliceFormat::fat64;
    if(field==3){o.slice.offset+=4096;o.application.offset+=4096;}
  }
  bool read(std::uintptr_t address,ImageOrigin& out)noexcept override{++calls;out=address==0x1000?application:cache;if(calls==mutate_at)mutate(out,field);return true;}
};
struct Hash final:DigestEngine{
  std::vector<std::vector<std::uint8_t>> frames;int updates{},fail_at{};std::uint64_t value{};
  bool begin()noexcept override{frames.emplace_back();value=1;return true;}
  bool update(const void* p,std::size_t n)noexcept override{++updates;auto b=static_cast<const std::uint8_t*>(p);frames.back().insert(frames.back().end(),b,b+n);for(std::size_t i=0;i<n;++i)value=value*33+b[i];return updates!=fail_at;}
  bool finish(Sha256& out)noexcept override{out={};for(unsigned i=0;i<8;++i)out[i]=static_cast<std::uint8_t>(value>>(8*i));return true;}
};
struct Fixture{Birth source;Nonce nonce;Files files;Images images;Origins origins;Hash hash;ProcessBirth birth{source,nonce};ManifestGuard manifest{{{"a",8256,tag(11)}},files};PlatformInventoryGuard guard{policy(),birth,manifest,images,origins,hash};};
void rejected(PlatformInventoryGuard& g,Failure why){const auto r=g.sample();CHECK(r.failure==why&&r.profile==IdentityProfile::unknown&&r.classified_images==Sha256{}&&!r.platform_assumed);CHECK(g.sample().failure==why);}
#ifdef SH3_TEST_NATIVE_HASH
std::string hex(const Sha256& b){std::string out;const char* h="0123456789abcdef";for(auto n:b){out+=h[n>>4];out+=h[n&15];}return out;}
#endif
void test(const std::string& name){
  Fixture f;
  if(name=="stable"){
    const auto first=f.guard.sample(),last=f.guard.sample();CHECK(first.failure==Failure::none&&last.failure==Failure::none);
    CHECK(first.profile==IdentityProfile::macos_platform_slices_v2&&first.platform_assumed&&first.application_images==1&&first.platform_images==1);
    CHECK(first.classified_images==last.classified_images&&first.file_objects==last.file_objects);
  }else if(name=="cross_profiles"){
    auto p=policy();p.profile=IdentityProfile::macos_platform_v1;PlatformInventoryGuard legacy(p,f.birth,f.manifest,f.images,f.origins,f.hash);rejected(legacy,Failure::invalid);
    Fixture missing;missing.origins.application.slice={};missing.origins.application.application.offset=0;rejected(missing.guard,Failure::invalid);
    Fixture thin;auto& app=thin.origins.application;app.application.offset=0;app.slice.offset=0;app.slice.size=file().size;app.slice.format=SliceFormat::thin;
    PlatformInventoryGuard legacy_thin(p,thin.birth,thin.manifest,thin.images,thin.origins,thin.hash);rejected(legacy_thin,Failure::invalid);
    CHECK(thin.guard.sample().failure==Failure::none);
  }else if(name=="invalid"){
    for(unsigned mode=0;mode<6;++mode){Fixture x;auto& app=x.origins.application;
      if(mode==0)app.slice={};if(mode==1)app.slice.offset++;if(mode==2)app.slice.size=UINT64_MAX;
      if(mode==3)app.slice.header[0]=0;if(mode==4)x.origins.cache.slice=app.slice;if(mode==5)app.slice.format=SliceFormat::thin;
      rejected(x.guard,Failure::invalid);
    }
  }else if(name=="changed"){
    for(int field=0;field<4;++field)for(int at:{1,3}){Fixture x;x.origins.mutate_at=at;x.origins.field=field;rejected(x.guard,Failure::changed);}
  }else if(name=="baseline"){
    for(int field=0;field<4;++field){Fixture x;CHECK(x.guard.sample().failure==Failure::none);Origins::mutate(x.origins.application,field);rejected(x.guard,Failure::changed);}
  }else if(name=="domains"){
    CHECK(f.guard.sample().failure==Failure::none);
    CHECK(std::string(f.hash.frames[0].begin(),f.hash.frames[0].begin()+21)=="SH3:platform-files:v2");
    CHECK(std::string(f.hash.frames[1].begin(),f.hash.frames[1].begin()+22)=="SH3:platform-images:v2");
    for(int field=0;field<4;++field){Fixture x;Origins::mutate(x.origins.application,field);CHECK(x.guard.sample().failure==Failure::none);CHECK(x.hash.frames[0]==f.hash.frames[0]&&x.hash.frames[1]!=f.hash.frames[1]);}
  }else if(name=="digest_failures"){
    CHECK(f.guard.sample().failure==Failure::none);for(int at=1;at<=f.hash.updates;++at){Fixture x;x.hash.fail_at=at;rejected(x.guard,Failure::digest);}
#ifdef SH3_TEST_NATIVE_HASH
  }else if(name=="vector"){
    MacOSSha256 hash;PlatformInventoryGuard g(policy(),f.birth,f.manifest,f.images,f.origins,hash);const auto r=g.sample();CHECK(r.failure==Failure::none);
    CHECK(hex(r.file_objects)==platform_slices_files_sha256&&hex(r.classified_images)==platform_slices_images_sha256);
#endif
  }else CHECK(false);
}
}
int main(int argc,char**argv){CHECK(argc==2);test(argv[1]);}
