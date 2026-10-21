#include "check.hpp"
#include "sh3_observer/external_waits.hpp"
#include <atomic>
#include <string>
#include <thread>
#include <vector>
using sh3::observer::ExternalWaits;
void scope() {
  ExternalWaits waits;CHECK(!waits.pending());
  {auto a=waits.wait();CHECK(a.tracked() && waits.pending());}
  CHECK(!waits.pending());
  {auto a=waits.wait(false);CHECK(!a.tracked() && !waits.pending());}
  CHECK(!waits.pending());
}
void nested() {
  ExternalWaits waits;
  {auto a=waits.wait();CHECK(a.tracked());
    {auto b=waits.wait();CHECK(b.tracked() && waits.pending());}
    CHECK(waits.pending());}
  CHECK(!waits.pending());
}
void capacity() {
  ExternalWaits zero(0);{auto a=zero.wait();CHECK(!a.tracked() && zero.pending());}
  CHECK(zero.pending());
  ExternalWaits one(1);
  {auto a=one.wait();CHECK(a.tracked());
    {auto b=one.wait();CHECK(!b.tracked() && one.pending());}
    CHECK(one.pending());}
  // No reset: accounting failure cannot turn into an admission later.
  CHECK(one.pending());{auto a=one.wait(false);CHECK(!a.tracked());}CHECK(one.pending());
}
void concurrent() {
  ExternalWaits waits;std::atomic<unsigned> entered=0,done=0;std::atomic_bool release_first=false,release_rest=false;
  std::vector<std::thread> threads;
  for(unsigned n=0;n<8;++n)threads.emplace_back([&,n]{
    {auto a=waits.wait();CHECK(a.tracked());entered.fetch_add(1);
      while(!(n==0?release_first.load():release_rest.load()))std::this_thread::yield();}
    done.fetch_add(1);
  });
  while(entered.load()!=8){std::this_thread::yield();}
  CHECK(waits.pending());release_first=true;
  while(done.load()!=1){std::this_thread::yield();}
  CHECK(waits.pending());release_rest=true;
  for(auto& t:threads){t.join();}
  CHECK(!waits.pending());
}
void publication() {
  ExternalWaits waits;std::atomic_bool entered=false,release=false;int effect=0;
  std::thread caller([&]{
    {auto a=waits.wait();CHECK(a.tracked());entered=true;
      while(!release.load()){std::this_thread::yield();}
      effect=71;}
  });
  while(!entered.load()){std::this_thread::yield();}
  CHECK(waits.pending());release=true;
  while(waits.pending()){std::this_thread::yield();}
  CHECK(effect==71);caller.join();
}
void unwind() {
  ExternalWaits waits;
  try{auto a=waits.wait();CHECK(a.tracked());throw 3;}catch(int value){CHECK(value==3);}
  CHECK(!waits.pending());
}
int main(int argc,char** argv) {
  CHECK(argc==2);const std::string n=argv[1];
  if(n=="scope")scope();else if(n=="nested")nested();else if(n=="capacity")capacity();
  else if(n=="concurrent")concurrent();else if(n=="publication")publication();
  else if(n=="unwind")unwind();else CHECK(false);
}
