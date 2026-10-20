#include "sh3_observer/inventory.hpp"
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
  Images(){value.addresses[0]=0x1000;value.addresses[1]=0x2000;value.count=2;value.revision=17;}
  bool read(ImageSnapshot& out) noexcept override {
    ++calls;out=value;if(calls==change_at)++out.revision;
    if(calls==invalid_at)out.revision=0;if(calls==address_at)++out.addresses[0];
    if(reverse && calls%2==0)std::swap(out.addresses[0],out.addresses[1]);return calls!=fail_at;
  }
};
struct Mappings final : MappingSource {
  int calls{},fail_at{},change_at{},invalid{};bool unknown{};std::uint64_t size=4096;
  bool read(std::uintptr_t address,MappedFile& out) noexcept override {
    ++calls;out={address,size,0,file(address==0x1000?1:0)};
    if(calls==change_at)++out.size;
    if(unknown)++out.file.inode;
    if(invalid==1)++out.address;if(invalid==2)out.size=0;if(invalid==3)out.offset=1;
    if(invalid==4)out.size=std::numeric_limits<std::uint64_t>::max();if(invalid==5)out.file.inode=0;
    return calls!=fail_at;
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
struct Fixture {
  Birth birth_source;Nonce nonce;Files files;Images images;Mappings mappings;Hash hash;
  ProcessBirth birth{birth_source,nonce};ManifestGuard manifest{config(),files};
  InventoryGuard guard{tag(170),birth,manifest,images,mappings,hash};
  int calls() const {return birth_source.calls+files.calls+images.calls+mappings.calls+hash.starts+hash.updates+hash.ends;}
};
void empty(const InventoryResult& out,InventoryFailure why) {
  CHECK(out.failure==why);CHECK(out.process.pid==0);CHECK(out.process.birth_ns==0);CHECK(out.process.nonce==ProcessNonce{});
  CHECK(out.file_objects==Sha256{});CHECK(out.loaded_images==Sha256{});CHECK(out.loader_revision==0);CHECK(out.image_count==0);
}
void terminal(Fixture& f,InventoryFailure why) {
  empty(f.guard.sample(),why);const auto calls=f.calls();
  f.birth_source.fail_at=0;f.files.fail_at=0;f.images.fail_at=0;f.mappings.fail_at=0;
  f.guard.lose();empty(f.guard.sample(),why);CHECK(f.calls()==calls);
}
void test(const std::string& name) {
  Fixture f;
  if(name=="capacity") {
    f.images.value.count=image_capacity;
    for(std::size_t i=0;i<image_capacity;++i)f.images.value.addresses[i]=0x1000*(i+1);
    CHECK(f.guard.sample().image_count==image_capacity);CHECK(f.mappings.calls==2*image_capacity);
  } else if(name=="stable"||name=="order") {
    f.images.reverse=name=="order";const auto first=f.guard.sample();CHECK(first.failure==InventoryFailure::none);
    CHECK(first.process.pid==7);CHECK(first.image_count==2);CHECK(first.loader_revision==17);
    CHECK(f.mappings.calls==4);CHECK(f.files.calls==8);CHECK(f.birth_source.calls==4);
    const auto again=f.guard.sample();CHECK(again.failure==InventoryFailure::none);
    CHECK(again.file_objects==first.file_objects);CHECK(again.loaded_images==first.loaded_images);
    CHECK(f.hash.frames[0]==f.hash.frames[2]);CHECK(f.hash.frames[1]==f.hash.frames[3]);
  } else if(name=="birth_error"||name=="birth_changed") {
    for(int i=1;i<=4;++i){Fixture x;if(name=="birth_error")x.birth_source.fail_at=i;else x.birth_source.change_at=i;terminal(x,InventoryFailure::birth);}
  } else if(name=="loader_error") {
    for(int i=1;i<=2;++i){Fixture x;x.images.fail_at=i;terminal(x,InventoryFailure::loader);}
  } else if(name=="invalid_inventory") {
    for(int i=0;i<6;++i){Fixture x;
      if(i==0)x.images.value.count=0;if(i==1)x.images.value.count=image_capacity+1;
      if(i==2)x.images.value.addresses[0]=0;if(i==3)x.images.value.addresses[1]=0x1000;
      if(i==4)x.images.value.revision=0;if(i==5)x.images.value.revision=UINT64_MAX;
      terminal(x,InventoryFailure::invalid);CHECK(x.files.calls==0);}
  } else if(name=="manifest_error"||name=="manifest_changed") {
    for(int i=1;i<=8;++i){Fixture x;if(name=="manifest_error")x.files.fail_at=i;else x.files.change_at=i;terminal(x,InventoryFailure::manifest);}
  } else if(name=="mapping_error") {
    for(int i=1;i<=4;++i){Fixture x;x.mappings.fail_at=i;terminal(x,InventoryFailure::mapping);}
  } else if(name=="invalid_mapping") {
    for(int i=1;i<=5;++i){Fixture x;x.mappings.invalid=i;terminal(x,InventoryFailure::invalid);}
  } else if(name=="uncovered") {
    f.mappings.unknown=true;terminal(f,InventoryFailure::uncovered);
  } else if(name=="ambiguous") {
    f.files.aliases=true;terminal(f,InventoryFailure::ambiguous);CHECK(f.mappings.calls==0);
  } else if(name=="mapping_changed") {
    for(int i=1;i<=4;++i){Fixture x;x.mappings.change_at=i;terminal(x,InventoryFailure::changed);}
  } else if(name=="loader_cycle") {
    f.images.change_at=2;terminal(f,InventoryFailure::changed);CHECK(f.hash.ends==2);
  } else if(name=="final_invalid") {
    f.images.invalid_at=2;terminal(f,InventoryFailure::invalid);
  } else if(name=="final_addresses") {
    f.images.address_at=2;terminal(f,InventoryFailure::changed);
  } else if(name=="baseline_revision") {
    CHECK(f.guard.sample().failure==InventoryFailure::none);f.images.value.revision+=2;terminal(f,InventoryFailure::changed);
  } else if(name=="baseline_mapping") {
    CHECK(f.guard.sample().failure==InventoryFailure::none);++f.mappings.size;terminal(f,InventoryFailure::changed);
  } else if(name=="digest_error") {
    CHECK(f.guard.sample().failure==InventoryFailure::none);
    for(int i=1;i<=2;++i){Fixture x;x.hash.start_fail=i;terminal(x,InventoryFailure::digest);}
    for(int i=1;i<=f.hash.updates;++i){Fixture x;x.hash.update_fail=i;terminal(x,InventoryFailure::digest);}
    for(int i=1;i<=2;++i){Fixture x;x.hash.end_fail=i;terminal(x,InventoryFailure::digest);}
  } else if(name=="digest_zero") {
    for(int i=1;i<=2;++i){Fixture x;x.hash.zero_at=i;terminal(x,InventoryFailure::digest);}
  } else if(name=="configuration") {
    InventoryGuard bad({},f.birth,f.manifest,f.images,f.mappings,f.hash);
    empty(bad.sample(),InventoryFailure::invalid);CHECK(f.calls()==0);
  } else if(name=="lose_empty"||name=="lose_ready") {
    if(name=="lose_ready")CHECK(f.guard.sample().failure==InventoryFailure::none);
    const auto calls=f.calls();f.guard.lose();terminal(f,InventoryFailure::lost);CHECK(f.calls()==calls);
  } else CHECK(false);
}
}
int main(int argc,char** argv) {CHECK(argc==2);test(argv[1]);}
