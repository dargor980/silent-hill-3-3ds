#include "image_census.hpp"
#include <cstdio>
#include <cstdlib>
#include <cstring>
#include <new>
#include <type_traits>
using namespace sh3::observer::probe;
#define CHECK(x) do { if (!(x)) { std::fprintf(stderr,"check failed line %d: %s\n",__LINE__,#x); std::abort(); } } while(false)
void* operator new(std::size_t) { std::abort(); }
void* operator new[](std::size_t) { std::abort(); }
void operator delete(void* p) noexcept { std::free(p); }
void operator delete[](void* p) noexcept { std::free(p); }
void operator delete(void* p, std::size_t) noexcept { std::free(p); }
void operator delete[](void* p, std::size_t) noexcept { std::free(p); }
void fill(ImageCensus& c, std::size_t count) { for(std::size_t i=1;i<=count;++i)c.add(i); }
void failed(ImageCensus& c,CensusFailure failure) {
  const auto before=c.observation(); CHECK(before.failure==failure);
  c.add(999999);c.remove(1);const auto after=c.observation();
  CHECK(after.events==before.events && after.active==before.active && after.failure==before.failure);
}
int main(int argc,char** argv) {
  CHECK(argc==2);const char* scenario=argv[1];ImageCensus c;
  const auto is=[&](const char* s){return !std::strcmp(scenario,s);};
  if(is("empty")) {const auto s=c.observation();CHECK(!s.events&&!s.active&&!s.peak&&!s.boundary_event&&s.failure==CensusFailure::none);}
  else if(is("add_remove")) {fill(c,3);c.remove(2);c.remove(3);c.remove(1);const auto s=c.observation();CHECK(s.events==6&&s.adds==3&&s.removes==3&&!s.active&&s.peak==3&&s.failure==CensusFailure::none);}
  else if(is("boundary_new")) {fill(c,1025);const auto s=c.observation();CHECK(s.active==1025&&s.boundary_event==1025&&s.boundary_address==1025&&s.boundary_kind==BoundaryKind::new_address&&s.failure==CensusFailure::none);}
  else if(is("boundary_duplicate")) {fill(c,1024);c.add(12);CHECK(c.observation().boundary_kind==BoundaryKind::duplicate&&c.observation().boundary_address==12);failed(c,CensusFailure::duplicate);}
  else if(is("boundary_null")) {fill(c,1024);c.add(0);CHECK(c.observation().boundary_kind==BoundaryKind::null_address);failed(c,CensusFailure::null_address);}
  else if(is("duplicate_before")) {c.add(7);c.add(7);CHECK(!c.observation().boundary_event);failed(c,CensusFailure::duplicate);}
  else if(is("null_add")) {c.add(0);failed(c,CensusFailure::null_address);}
  else if(is("unknown_remove")) {c.add(1);c.remove(2);failed(c,CensusFailure::unknown_remove);}
  else if(is("null_remove")) {c.add(1);c.remove(0);failed(c,CensusFailure::null_address);}
  else if(is("capacity")) {fill(c,census_capacity);CHECK(c.observation().active==census_capacity&&c.observation().failure==CensusFailure::none);}
  else if(is("over_capacity")) {fill(c,census_capacity+1);CHECK(c.observation().active==census_capacity);failed(c,CensusFailure::capacity);}
  else if(is("event_budget")) {for(std::size_t i=0;i<census_event_budget/2;++i){c.add(1);c.remove(1);}CHECK(c.observation().events==census_event_budget&&c.observation().failure==CensusFailure::none);c.add(2);failed(c,CensusFailure::event_budget);}
  else if(is("remove_readd")) {fill(c,10);c.remove(5);c.add(5);CHECK(c.observation().active==10&&c.observation().events==12&&c.observation().failure==CensusFailure::none);}
  else if(is("high_addresses")) {c.add(UINTPTR_MAX);c.add(UINTPTR_MAX-1);c.remove(UINTPTR_MAX);CHECK(c.observation().active==1&&c.observation().failure==CensusFailure::none);}
  else if(is("boundary_after_remove")) {fill(c,1024);c.remove(10);c.add(1025);CHECK(!c.observation().boundary_event);c.add(10);CHECK(c.observation().boundary_event==1027&&c.observation().boundary_kind==BoundaryKind::new_address);c.remove(10);c.add(1026);CHECK(c.observation().boundary_event==1027);}
  else if(is("size")) {static_assert(std::is_trivially_destructible_v<ImageCensus>);CHECK(sizeof(ImageCensus)<=40*1024&&sizeof(CensusObservation)<=256);std::printf("CENSUS_BYTES=%zu OBSERVATION_BYTES=%zu\n",sizeof(ImageCensus),sizeof(CensusObservation));}
  else CHECK(false);
}
