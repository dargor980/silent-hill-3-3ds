#include "check.hpp"
#include "sh3_observer/host_epoch.hpp"
#include "sh3_observer/physical_writes.hpp"
#include <algorithm>
#include <array>
#include <limits>
#include <string>
#include <thread>
#include <type_traits>
#include <vector>
using namespace sh3::observer;
constexpr auto maximum = std::numeric_limits<std::uint64_t>::max();
constexpr std::uint64_t base = 1ULL << 40;
LifetimePlan plan() { return {{{{1}}, 7, 100, 1000}, {0x1000, 0x2000, 0x3000, 0x4000}, 1000}; }
void epoch_test() {
  static_assert(!std::is_copy_constructible_v<HostEpoch> && !std::is_move_constructible_v<HostEpoch>);
  HostEpoch epoch; CHECK(epoch.current() == 1);
  for (std::uint64_t n=2; n<200; ++n) CHECK(epoch.advance() == n && epoch.current() == n);
}
void exhaustion() {
  HostEpoch epoch(maximum-1); CHECK(epoch.advance() == maximum); CHECK(epoch.advance() == 0);
  for (unsigned n=0; n<20; ++n) CHECK(epoch.advance() == 0 && epoch.current() == 0);
  HostEpoch unavailable(0); CHECK(unavailable.advance() == 0);
}
void concurrent_epoch() {
  HostEpoch epoch;
  std::array<std::array<std::uint64_t,256>,8> values{};
  std::vector<std::thread> threads;
  for (auto& row:values) threads.emplace_back([&epoch,&row]{ for(auto& v:row) v=epoch.advance(); });
  for(auto& t:threads)t.join();
  std::vector<std::uint64_t> ordered;
  for(const auto& row:values)ordered.insert(ordered.end(),row.begin(),row.end());
  std::sort(ordered.begin(),ordered.end());
  for(std::size_t i=0;i<ordered.size();++i)CHECK(ordered[i]==i+2);
  CHECK(epoch.current()==2049);
}
void causes() {
  const std::array kinds{LifetimeKind::reset,LifetimeKind::restore,LifetimeKind::remap,LifetimeKind::settings,LifetimeKind::shutdown,LifetimeKind::lost};
  const std::array reasons{LifetimeReason::reset,LifetimeReason::restore,LifetimeReason::remap,LifetimeReason::settings,LifetimeReason::shutdown,LifetimeReason::lost};
  for(std::size_t i=0;i<kinds.size();++i){
    LifetimeGuard g;CHECK(g.arm(plan()));PhysicalWrites p(g,base);WriteBinding binding(p);CHECK(binding.connected());
    const auto old=host_epoch();before_lifecycle(kinds[i],1001);
    CHECK(host_epoch()==old+1);CHECK(g.report().reason==reasons[i]);CHECK(g.report().state==LifetimeState::failed);
    before_host_write(base+0x3000,4,1001);before_lifecycle(LifetimeKind::restore,0);
    CHECK(g.report().reason==reasons[i]);CHECK(host_epoch()==old+2);
  }
}
void invalid_kind() {
  for(auto kind:{LifetimeKind::write,LifetimeKind::checkpoint,LifetimeKind::finish,LifetimeKind::cancel,static_cast<LifetimeKind>(255)}){
    LifetimeGuard g;CHECK(g.arm(plan()));PhysicalWrites p(g,base);CHECK(!p.lifecycle(kind,1001));CHECK(g.report().reason==LifetimeReason::lost);
  }
}
void binding_test() {
  const auto initial=host_epoch();before_lifecycle(LifetimeKind::reset,0);CHECK(host_epoch()==initial+1);
  LifetimeGuard g;CHECK(g.arm(plan()));PhysicalWrites p(g,base);
  {WriteBinding first(p);WriteBinding second(p);CHECK(first.connected()&&!second.connected());before_lifecycle(LifetimeKind::restore,1001);CHECK(g.report().reason==LifetimeReason::restore);}
  before_lifecycle(LifetimeKind::shutdown,0);CHECK(host_epoch()==initial+3);CHECK(g.report().reason==LifetimeReason::restore);
  LifetimeGuard fresh;auto next=plan();next.begin.epoch=host_epoch();CHECK(fresh.arm(next));PhysicalWrites q(fresh,base);
  {WriteBinding binding(q);CHECK(binding.connected());before_lifecycle(LifetimeKind::remap,1001);CHECK(fresh.report().reason==LifetimeReason::remap);}
  // A new session/admission protocol must still authenticate this epoch and quiesce effects.
}
void terminal() {
  LifetimeGuard sealed;CHECK(sealed.arm(plan()));CHECK(sealed.notify({{{{1}},7,101,1001},LifetimeKind::finish,0,0}));
  PhysicalWrites p(sealed,base);{WriteBinding binding(p);const auto before=host_epoch();before_lifecycle(LifetimeKind::reset,0);CHECK(host_epoch()==before+1);CHECK(sealed.report().state==LifetimeState::sealed);}
  LifetimeGuard rewind;CHECK(rewind.arm(plan()));PhysicalWrites q(rewind,base);CHECK(!q.lifecycle(LifetimeKind::restore,999));CHECK(rewind.report().reason==LifetimeReason::cycle);
  CHECK(!rewind.arm(plan()));
}
void concurrent_notices() {
  LifetimeGuard g;CHECK(g.arm(plan()));PhysicalWrites p(g,base);WriteBinding binding(p);
  const auto initial=host_epoch();std::vector<std::thread> threads;
  for(unsigned i=0;i<8;++i)threads.emplace_back([]{for(unsigned j=0;j<100;++j){before_host_write(base+0x5000,4,1001);before_lifecycle(LifetimeKind::restore,1001);}});
  for(auto& t:threads){t.join();}
  CHECK(host_epoch()==initial+800);CHECK(g.report().reason==LifetimeReason::restore);
  // No guest memory is written here; this proves callback serialization only.
}
int main(int argc,char** argv){
  CHECK(argc==2);const std::string name=argv[1];
  if(name=="epoch")epoch_test();else if(name=="exhaustion")exhaustion();else if(name=="concurrent_epoch")concurrent_epoch();else if(name=="causes")causes();else if(name=="invalid_kind")invalid_kind();else if(name=="binding")binding_test();else if(name=="terminal")terminal();else if(name=="concurrent_notices")concurrent_notices();else CHECK(false);
}
