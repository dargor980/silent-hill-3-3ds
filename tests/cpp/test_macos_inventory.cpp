#include "sh3_observer/inventory.hpp"
#include "sh3_observer/macos_artifact_manifest.hpp"
#include "sh3_observer/macos_image_identity.hpp"
#include "sh3_observer/macos_process_birth.hpp"
#include "check.hpp"
#include <algorithm>
#include <dlfcn.h>
#include <filesystem>
#include <fstream>
#include <unistd.h>
using namespace sh3::observer;
namespace fs=std::filesystem;
namespace {
Sha256 tag(std::uint8_t value) {Sha256 out{};out[0]=value;return out;}
Sha256 hex(const std::string& value) {
  CHECK(value.size()==64);Sha256 out{};
  for(std::size_t i=0;i<32;++i)out[i]=static_cast<std::uint8_t>(std::stoul(value.substr(2*i,2),nullptr,16));return out;
}
struct Library {
  void* handle{};std::uintptr_t header{};
  explicit Library(const fs::path& path) {
    handle=dlopen(path.c_str(),RTLD_NOW|RTLD_LOCAL);CHECK(handle);
    auto symbol=dlsym(handle,"sh3_image_fixture");CHECK(symbol);Dl_info info{};
    CHECK(dladdr(symbol,&info));header=reinterpret_cast<std::uintptr_t>(info.dli_fbase);CHECK(header);
  }
  ~Library(){if(handle)CHECK(dlclose(handle)==0);}
};
struct Events final : ImageSnapshotSource {
  // Test-only projection. Full mode always uses the entire real inventory.
  std::uintptr_t fixture{};bool full{};
  bool read(ImageSnapshot& out) noexcept override {
    if(!MacOSImageEvents::read(out))return false;
    if(full)return true;
    if(std::find(out.addresses.begin(),out.addresses.begin()+out.count,fixture)==out.addresses.begin()+out.count)return false;
    out.addresses={};out.addresses[0]=fixture;out.count=1;return true;
  }
};
struct HookHash final : DigestEngine {
  MacOSSha256 hash;fs::path cycle;int starts{};
  bool begin() noexcept override {
    if(++starts==2&&!cycle.empty()){Library transient(cycle);}
    return hash.begin();
  }
  bool update(const void* p,std::size_t n) noexcept override {return hash.update(p,n);}
  bool finish(Sha256& out) noexcept override {return hash.finish(out);}
};
Sha256 fixture_hash(const fs::path& path) {
  std::ifstream in(path,std::ios::binary);CHECK(in.good());MacOSSha256 hash;CHECK(hash.begin());
  std::array<char,digest_block_size> data{};
  while(in){in.read(data.data(),data.size());auto got=in.gcount();if(got>0)CHECK(hash.update(data.data(),static_cast<std::size_t>(got)));}
  CHECK(in.eof());Sha256 out{};CHECK(hash.finish(out));return out;
}
void native(const std::string& scenario,const fs::path& first,const fs::path& other,const fs::path& base) {
  fs::create_directories(base);auto pattern=(base/"case-XXXXXX").string();CHECK(mkdtemp(pattern.data()));const fs::path dir=pattern;
  const auto named=dir/"loaded.dylib";CHECK(fs::copy_file(first,named));
  const std::vector<ExpectedFile> expected{{"loaded.dylib",fs::file_size(named),fixture_hash(named)}};
  ImageSnapshot initial{};CHECK(MacOSImageEvents::read(initial));Library library(named);
  Events events;events.fixture=library.header;events.full=scenario=="full_inventory_rejected";
  MacOSBirthSource births;MacOSNonceSource entropy;ProcessBirth birth(births,entropy);
  MacOSArtifactFiles files(dir.string(),expected);ManifestGuard manifest(expected,files);
  MacOSMappingSource maps;HookHash hash;if(scenario=="fixture_during_hash")hash.cycle=other;
  InventoryGuard guard(tag(170),birth,manifest,events,maps,hash);
  auto before=guard.sample();
  if(scenario=="full_inventory_rejected") {
    // Executable/system images are not covered by the fixture manifest.
    CHECK(before.failure==InventoryFailure::uncovered||before.failure==InventoryFailure::mapping);
    CHECK(before.process.pid==0);CHECK(before.image_count==0);CHECK(before.loaded_images==Sha256{});
    CHECK(guard.sample().failure==before.failure);return;
  }
  if(scenario=="fixture_during_hash") {
    CHECK(before.failure==InventoryFailure::changed);CHECK(before.image_count==0);CHECK(guard.sample().failure==before.failure);return;
  }
  CHECK(before.failure==InventoryFailure::none);CHECK(before.process.pid==static_cast<std::uint32_t>(getpid()));CHECK(before.image_count==1);
  if(scenario=="fixture_stable") {
    auto again=guard.sample();CHECK(again.failure==InventoryFailure::none);
    CHECK(again.file_objects==before.file_objects);CHECK(again.loaded_images==before.loaded_images);return;
  }
  InventoryFailure wanted{};
  if(scenario=="fixture_replace") {
    CHECK(fs::copy_file(first,dir/"replacement.dylib"));fs::rename(dir/"replacement.dylib",named);wanted=InventoryFailure::manifest;
  } else if(scenario=="fixture_cycle") {
    {Library transient(other);}wanted=InventoryFailure::changed;
  } else CHECK(false);
  auto result=guard.sample();CHECK(result.failure==wanted);CHECK(result.image_count==0);CHECK(result.process.pid==0);
  CHECK(guard.sample().failure==wanted);
}
void vector() {
  struct B final : BirthSource {bool read(BirthReading& out) noexcept override {out={7,8,9};return true;}} b;
  struct N final : NonceSource {bool fill(ProcessNonce& out) noexcept override {out={};out[0]=1;return true;}} n;
  struct F final : ArtifactSource {
    bool read(std::string_view name,FileDigest& out) noexcept override {const unsigned i=name=="a"?0:1;out={{1,10+i,64,3,4,5,6},tag(i==0?11:22)};return true;}
  } f;
  struct E final : ImageSnapshotSource {
    bool read(ImageSnapshot& out) noexcept override {out={};out.addresses[0]=0x2000;out.addresses[1]=0x1000;out.count=2;out.revision=17;return true;}
  } e;
  struct M final : MappingSource {
    bool read(std::uintptr_t address,MappedFile& out) noexcept override {out={address,4096,0,{1,address==0x1000?11U:10U,64,3,4,5,6}};return true;}
  } m;
  ProcessBirth birth(b,n);ManifestGuard manifest({{"a",64,tag(11)},{"b",64,tag(22)}},f);MacOSSha256 hash;
  InventoryGuard guard(tag(170),birth,manifest,e,m,hash);auto result=guard.sample();CHECK(result.failure==InventoryFailure::none);
  // Independently encoded with Python struct.pack('<Q') and hashlib.sha256.
  CHECK(result.file_objects==hex("e9e0c3ba85dbf630314be9793bd1b6262c3e95db20d07a88f8135255b445f7e7"));
  CHECK(result.loaded_images==hex("b0897511bc6aa6a4f03c9462e89e30db96226afcee906668198a8e8bad128373"));
}
}
int main(int argc,char** argv) {
  CHECK(argc==5);if(std::string(argv[1])=="canonical_vector")vector();else native(argv[1],argv[2],argv[3],argv[4]);
}
