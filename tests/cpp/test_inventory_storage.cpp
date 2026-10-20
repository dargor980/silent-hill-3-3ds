#include "sh3_observer/platform_inventory.hpp"
#include "check.hpp"
#include <chrono>
#include <cstdio>
#include <cstdlib>
#include <cstring>
#include <new>
#include <pthread.h>
#include <type_traits>

using namespace sh3::observer;
namespace {
bool deny{}, track{};
std::size_t allocations{}, frees{}, allocation_bytes{};
void* tracked{};
void* allocate(std::size_t bytes) noexcept {
  if (deny) return nullptr;
  void* value = std::malloc(bytes);
  if (track && value) { ++allocations; allocation_bytes=bytes; tracked=value; }
  return value;
}
void release(void* value) noexcept {
  if (value && value==tracked) { ++frees; tracked=nullptr; }
  std::free(value);
}
Sha256 tag(unsigned n) { Sha256 value{}; value[0]=n; return value; }
FileObject object() { return {1,2,64,3,4,5,6}; }
struct Birth final : BirthSource {
  unsigned calls{};
  bool read(BirthReading& out) noexcept override { ++calls; out={7,8,9}; return true; }
};
struct Nonce final : NonceSource {
  bool fill(ProcessNonce& out) noexcept override { out={}; out[0]=1; return true; }
};
struct Files final : ArtifactSource {
  unsigned calls{};
  bool read(std::string_view, FileDigest& out) noexcept override { ++calls; out={object(),tag(11)}; return true; }
};
struct Images final : ImageSnapshotSource {
  unsigned calls{}; std::uint64_t revision{17};
  bool read(ImageSnapshot& out) noexcept override {
    ++calls; out={}; out.count=image_capacity; out.revision=revision;
    for (std::size_t i=0;i<out.count;++i) out.addresses[i]=0x1000*(i+1);
    return true;
  }
};
struct Mapping final : MappingSource {
  unsigned calls{};
  bool read(std::uintptr_t address, MappedFile& out) noexcept override {
    ++calls; out={address,4096,0,object()}; return true;
  }
};
struct Origins final : ImageOriginSource {
  unsigned calls{};
  bool read(std::uintptr_t address, ImageOrigin& out) noexcept override {
    ++calls; out={};
    if (address==0x1000) { out.kind=ImageOriginKind::application; out.application={address,4096,0,object()}; }
    else { out.kind=ImageOriginKind::platform_cache; out.cache={address,0x1000,0x2000000,{}}; out.cache.uuid[0]=9; }
    return true;
  }
};
struct Hash final : DigestEngine {
  std::uint64_t value{};
  bool begin() noexcept override { value=1; return true; }
  bool update(const void* raw, std::size_t size) noexcept override {
    const auto* bytes=static_cast<const unsigned char*>(raw);
    for (std::size_t i=0;i<size;++i) value=value*33+bytes[i];
    return true;
  }
  bool finish(Sha256& out) noexcept override { out={}; for(unsigned i=0;i<8;++i) out[i]=value>>(8*i); return true; }
};
struct Fixture {
  Birth source; Nonce nonce; Files files; Images images; Mapping mapping; Origins origins; Hash hash;
  ProcessBirth birth{source,nonce}; ManifestGuard manifest{{{"a",64,tag(11)}},files};
  PlatformPolicy policy{IdentityProfile::macos_platform_v1,tag(3),tag(4),tag(5),{},0x1000,0};
  Fixture() { policy.expected_cache[0]=9; }
  unsigned calls() const { return source.calls+files.calls+images.calls+mapping.calls+origins.calls; }
};
void sample(InventoryGuard& guard) { const auto r=guard.sample(); CHECK(r.failure==InventoryFailure::none && r.image_count==2048); }
void sample(PlatformInventoryGuard& guard) { const auto r=guard.sample(); CHECK(r.failure==PlatformInventoryFailure::none && r.application_images==1 && r.platform_images==2047); }
template<class Guard, class Factory> void exercise(bool oom, Factory factory, Fixture& f) {
  const auto before=allocations; deny=oom; track=true;
  {
    Guard guard=factory();
    track=false;
    if (oom) {
      CHECK(allocations==before); deny=false;
      const auto r=guard.sample(); CHECK(r.failure==decltype(r.failure)::storage);
      CHECK(r.process.pid==0 && r.loader_revision==0); guard.lose();
      CHECK(guard.sample().failure==decltype(r.failure)::storage && f.calls()==0);
    } else {
      CHECK(allocations==before+1);
      CHECK(allocation_bytes<=(std::is_same_v<Guard,InventoryGuard> ? 256u : 512u)*1024);
      deny=true; sample(guard); sample(guard); deny=false;
      CHECK(allocations==before+1);
      std::printf("guard=%zu workspace=%zu\n",sizeof(Guard),allocation_bytes);
    }
  }
  CHECK(oom || frees==allocations);
}
void both() {
  Fixture f;
  exercise<InventoryGuard>(false,[&] { return InventoryGuard(tag(3),f.birth,f.manifest,f.images,f.mapping,f.hash); },f);
  Fixture p;
  exercise<PlatformInventoryGuard>(false,[&] { return PlatformInventoryGuard(p.policy,p.birth,p.manifest,p.images,p.origins,p.hash); },p);
}
void* on_stack(void*) {
  const auto start=std::chrono::steady_clock::now();
  both();
  const auto micros=std::chrono::duration_cast<std::chrono::microseconds>(std::chrono::steady_clock::now()-start).count();
  CHECK(micros<5000000);
  std::printf("stack_requested=524288 synthetic_four_samples_us=%lld\n",static_cast<long long>(micros));
  return nullptr;
}
}
void* operator new(std::size_t n) { if(void* p=allocate(n))return p; throw std::bad_alloc(); }
void* operator new[](std::size_t n) { return ::operator new(n); }
void* operator new(std::size_t n,const std::nothrow_t&) noexcept { return allocate(n); }
void* operator new[](std::size_t n,const std::nothrow_t&) noexcept { return allocate(n); }
void operator delete(void* p) noexcept { release(p); }
void operator delete[](void* p) noexcept { release(p); }
void operator delete(void* p,std::size_t) noexcept { release(p); }
void operator delete[](void* p,std::size_t) noexcept { release(p); }
void operator delete(void* p,const std::nothrow_t&) noexcept { release(p); }
void operator delete[](void* p,const std::nothrow_t&) noexcept { release(p); }
int main(int argc,char** argv) {
  CHECK(argc==2); const char* mode=argv[1];
  if (!std::strcmp(mode,"stack")) {
    pthread_attr_t attr; CHECK(!pthread_attr_init(&attr)); CHECK(!pthread_attr_setstacksize(&attr,512*1024));
    std::size_t size{}; CHECK(!pthread_attr_getstacksize(&attr,&size) && size==512*1024);
    pthread_t thread; CHECK(!pthread_create(&thread,&attr,on_stack,nullptr)); CHECK(!pthread_attr_destroy(&attr)); CHECK(!pthread_join(thread,nullptr));
  } else if (!std::strcmp(mode,"isolation")) {
    Fixture a,b;
    InventoryGuard first(tag(3),a.birth,a.manifest,a.images,a.mapping,a.hash), second(tag(3),b.birth,b.manifest,b.images,b.mapping,b.hash);
    sample(first); sample(second); ++a.images.revision; CHECK(first.sample().failure==InventoryFailure::changed); sample(second);
    Fixture c,d;
    PlatformInventoryGuard third(c.policy,c.birth,c.manifest,c.images,c.origins,c.hash), fourth(d.policy,d.birth,d.manifest,d.images,d.origins,d.hash);
    sample(third); sample(fourth); ++c.images.revision; CHECK(third.sample().failure==PlatformInventoryFailure::changed); sample(fourth);
  } else {
    Fixture f; const bool oom=std::strstr(mode,"oom")!=nullptr;
    if (!std::strcmp(mode,"strict") || !std::strcmp(mode,"strict_oom"))
      exercise<InventoryGuard>(oom,[&] { return InventoryGuard(tag(3),f.birth,f.manifest,f.images,f.mapping,f.hash); },f);
    else if (!std::strcmp(mode,"platform") || !std::strcmp(mode,"platform_oom"))
      exercise<PlatformInventoryGuard>(oom,[&] { return PlatformInventoryGuard(f.policy,f.birth,f.manifest,f.images,f.origins,f.hash); },f);
    else CHECK(false);
  }
}
