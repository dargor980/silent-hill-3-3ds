#include "inventory_timing_probe.hpp"
#include <cassert>
int main() {
  using namespace sh3_it;
  Counter c;
  assert(c.record(10,20,true,7)); assert(c.record(30,30,false,2));
  assert(c.calls==2 && c.complete==1 && c.total==10 && c.minimum==0 && c.maximum==10 && c.bytes==9);
  assert(c.first==10 && c.last==30);
  assert(!c.record(50,49,true,0) && c.calls==2);
  c.total=UINT64_MAX; assert(!c.record(0,1,false,0));
  c={}; c.bytes=UINT64_MAX; assert(!c.record(0,0,false,1));
  c={}; c.calls=UINT64_MAX; assert(!c.record(0,0,true,0));
  data.fine=false;
  { Span disabled(file_read,true); disabled.done(90); }
  assert(!data.counters[0][file_read].calls);
  { Span outer(prepare); { Span inner(construct);inner.done(); } outer.done();outer.stop();outer.stop(); }
  assert(data.counters[0][prepare].calls==1 && data.counters[0][construct].calls==1);
  assert(data.counters[0][prepare].total>=data.counters[0][construct].total);
  data.next(); { Span partial(sample); }
  assert(data.counters[1][sample].calls==1 && data.counters[1][sample].complete==0);
  data.fine=true; { Span read(file_read,true);read.done(64); }
  assert(data.counters[1][file_read].bytes==64);
  data.next();data.next();data.next();assert(data.query==3 && data.errors==1);
  for(unsigned i=0;i<17;++i) mark("test");
  assert(data.event_count==16 && data.errors==2);
  calibrate(); assert(data.calibration_calls==10000 && data.calibration_ns>0);
}
