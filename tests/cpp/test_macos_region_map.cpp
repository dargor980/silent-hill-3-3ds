#include "sh3_observer/macos_region_map.hpp"
#include "check.hpp"
#include <cerrno>
#include <cstring>
#include <string>
#include <sys/mman.h>
#include <sys/wait.h>
#include <unistd.h>
using namespace sh3::observer;
namespace {
struct Mapping {
  std::size_t page = static_cast<std::size_t>(sysconf(_SC_PAGESIZE));
  void* base = mmap(nullptr,3*page,PROT_NONE,MAP_PRIVATE|MAP_ANON,-1,0);
  Mapping() { CHECK(base != MAP_FAILED); CHECK(mprotect(middle(),page,PROT_READ|PROT_WRITE) == 0); }
  void* middle() { return static_cast<char*>(base)+page; }
  ~Mapping() { CHECK(munmap(base,3*page) == 0); }
};
void self() {
  struct Counted final : RegionSource {
    MacOSRegionSource source; unsigned calls{};
    RegionQuery query(std::uint64_t cursor, VmRegion& r) noexcept override { ++calls; return source.query(cursor,r); }
  } counted;
  Mapping m; MacOSRegionSource s; RegionMap map;
  const auto status = read_region_map(counted,map);
  bool capacity_expected = false;
#if defined(__has_feature)
#if __has_feature(address_sanitizer)
  // ASan can create more than 65536 mappings. Verify bounded refusal, not a prefix.
  capacity_expected = status == RegionFailure::capacity;
#endif
#endif
  if (capacity_expected) CHECK(counted.calls == region_capacity+1 && map.regions.empty() && map.bytes == 0);
  else CHECK(status == RegionFailure::none && !map.regions.empty() && map.bytes > 0);
  auto address = reinterpret_cast<std::uint64_t>(m.middle()); bool seen = false;
  for (const auto& r : map.regions) if (r.address <= address && address < r.address+r.size) {
    CHECK(r.protection == 3 && !r.submap); seen = true;
  }
  CHECK(seen || capacity_expected);
  VmRegion r{}; CHECK(s.query(address,r) == RegionQuery::found && r.address <= address && address < r.address+r.size);
  CHECK(mprotect(m.middle(),m.page,PROT_READ) == 0);
  VmRegion after{}; CHECK(s.query(address,after) == RegionQuery::found && after.protection == 1 && !same_region(r,after));
}
void forked() {
  MacOSRegionSource s; const auto pid = fork(); CHECK(pid >= 0);
  if (pid == 0) { VmRegion r{}; r.size = 99; CHECK(s.query(0,r) == RegionQuery::unavailable && same_region(r,{})); _exit(0); }
  int status{}; pid_t waited;
  do { waited = waitpid(pid,&status,0); } while (waited < 0 && errno == EINTR);
  CHECK(waited == pid && WIFEXITED(status) && WEXITSTATUS(status) == 0);
}
struct Mutation final : RegionSource {
  Mapping m;
  MacOSRegionSource source;
  unsigned pass{};
  RegionQuery query(std::uint64_t cursor, VmRegion& r) noexcept override {
    // Fixture-scoped source: the real native query, not a whole-process census.
    if (cursor != 0) return RegionQuery::end;
    if (++pass == 2) CHECK(mprotect(m.middle(),m.page,PROT_READ) == 0);
    return source.query(reinterpret_cast<std::uint64_t>(m.middle()),r);
  }
};
void mutation() {
  Mutation s; RegionMap map;
  CHECK(read_region_map(s,map) == RegionFailure::changed && map.regions.empty() && map.bytes == 0 && s.pass == 2);
}
struct Api {
  int calls{}, pid{42}, change_at{}, kernel_calls{};
  kern_return_t result{KERN_SUCCESS};
  int count_delta{}, submap{}, external{1};
} api;
int fake_pid() { ++api.calls; return api.change_at && api.calls >= api.change_at ? 43 : api.pid; }
kern_return_t fake_region(vm_map_read_t task, mach_vm_address_t* address, mach_vm_size_t* size,
                         natural_t* depth, vm_region_recurse_info_t out, mach_msg_type_number_t* count) {
  ++api.kernel_calls;
  CHECK(task == mach_task_self() && *address == 16 && *size == 0 && *depth == region_depth_limit && *count == VM_REGION_SUBMAP_INFO_V2_COUNT_64);
  vm_region_submap_info_data_64_t i{};
  i.offset = 8192; i.object_id_full = 0x123456789abcdef0ULL; i.object_id = 7;
  i.protection = 3; i.max_protection = 7; i.inheritance = 1; i.user_tag = 230;
  i.shadow_depth = 3; i.share_mode = 4; i.external_pager = api.external; i.is_submap = api.submap;
#ifdef VM_REGION_FLAG_JIT_ENABLED
  i.flags = VM_REGION_FLAG_JIT_ENABLED;
#endif
  i.pages_resident = 222; i.ref_count = 5; // Volatile counters must not affect identity.
  std::memcpy(out,&i,sizeof(i)); *address = 4096; *size = 4096; *depth = 2; *count += api.count_delta;
  return api.result;
}
void fake() {
  for (unsigned n = 0; n < 11; ++n) {
    api = {}; MacOSRegionCalls c{fake_pid,fake_region};
    if (n == 0) c.pid = nullptr;
    if (n == 1) c.region = nullptr;
    if (n == 2) api.pid = 0;
    if (n == 3) api.change_at = 2;
    if (n == 4) api.change_at = 3;
    if (n == 5) api.result = KERN_FAILURE;
    if (n == 6) api.count_delta = -1;
    if (n == 7) api.count_delta = 1;
    if (n == 8) api.external = 2;
    if (n == 9) api.submap = 2;
    if (n == 10) { api.result = KERN_INVALID_ADDRESS; api.change_at = 3; }
    MacOSRegionSource s(c); VmRegion r{}; r.size = 99;
    CHECK(s.query(16,r) == RegionQuery::unavailable && same_region(r,{}));
  }
  api = {}; MacOSRegionSource s({fake_pid,fake_region}); VmRegion r{};
  CHECK(s.query(16,r) == RegionQuery::found && r.address == 4096 && r.size == 4096 && r.offset == 8192);
  CHECK(r.object == 0x123456789abcdef0ULL && r.depth == 2 && r.protection == 3 && r.maximum_protection == 7);
  CHECK(r.inheritance == 1 && r.tag == 230 && r.shadow_depth == 3 && r.share_mode == 4 && r.external && !r.submap);
#ifdef VM_REGION_FLAG_JIT_ENABLED
  CHECK(r.flags_available && r.flags == VM_REGION_FLAG_JIT_ENABLED);
#else
  CHECK(!r.flags_available && r.flags == 0);
#endif
  api.result = KERN_INVALID_ADDRESS;
  CHECK(s.query(16,r) == RegionQuery::end && same_region(r,{}));
  api.result = KERN_SUCCESS; api.submap = 1;
  CHECK(s.query(16,r) == RegionQuery::found && r.submap);
}
}
int main(int argc, char** argv) {
  CHECK(argc == 2); const std::string name = argv[1];
  if (name == "self") self(); else if (name == "fork") forked();
  else if (name == "mutation") mutation(); else if (name == "api") fake(); else CHECK(false);
}
