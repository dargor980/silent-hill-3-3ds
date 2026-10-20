#include "sh3_observer/page_binding.hpp"
#include "check.hpp"
#include <string>
using namespace sh3::observer;
namespace {
struct File final : PageFileSource {
  PageFileReading value{{1,2,16384,3,4,5,6},{42,0,true,true,false}};
  int calls{},error_at{},change_at{};
  bool read(PageFileReading& out) noexcept override {
    ++calls;out=value;if(calls==change_at)++out.file.inode;return calls!=error_at;
  }
};
struct Pages final : PageSource {
  PageReading value{42,123,true,true,false};int calls{},error_at{},change_at{};
  bool read(std::uintptr_t address,PageReading& out) noexcept override {
    CHECK(address==0x1000);++calls;out=value;if(calls==change_at)++out.offset;return calls!=error_at;
  }
};
void empty(const PageBindingResult& r,PageFailure why) {
  CHECK(r.failure==why);CHECK(r.file.inode==0);CHECK(r.file.device==0);CHECK(r.file.size==0);CHECK(r.object==0);CHECK(r.offset==0);
}
void terminal(PageBinding& g,File& f,Pages& p,PageFailure why) {
  empty(g.sample(),why);const auto calls=f.calls+p.calls;
  f.error_at=p.error_at=0;f.change_at=p.change_at=0;
  g.lose();empty(g.sample(),why);CHECK(f.calls+p.calls==calls);
}
void test(const std::string& name) {
  File f;Pages p;PageBinding g(0x1000,f,p);
  if(name=="stable") {
    const auto r=g.sample();CHECK(r.failure==PageFailure::none);CHECK(r.file.inode==2);CHECK(r.object==42);CHECK(r.offset==123);
    CHECK(f.calls==2&&p.calls==2);CHECK(g.sample().failure==PageFailure::none);
  } else if(name=="zero_address") {
    PageBinding invalid(0,f,p);terminal(invalid,f,p,PageFailure::invalid);CHECK(f.calls+p.calls==0);
  } else if(name=="file_error"||name=="page_error") {
    for(int i=1;i<=2;++i){File a;Pages b;if(name=="file_error")a.error_at=i;else b.error_at=i;PageBinding x(0x1000,a,b);terminal(x,a,b,PageFailure::unavailable);}
  } else if(name=="file_change"||name=="offset_change") {
    for(int i=1;i<=2;++i){File a;Pages b;if(name=="file_change")a.change_at=i;else b.change_at=i;PageBinding x(0x1000,a,b);terminal(x,a,b,PageFailure::changed);}
  } else if(name=="invalid_reference"||name=="invalid_target") {
    for(int i=0;i<4;++i){File a;Pages b;auto& page=name=="invalid_reference"?a.value.page:b.value;
      if(i==0)page.object=0;if(i==1)page.resident=false;if(i==2)page.external=false;if(i==3)page.modified=true;
      PageBinding x(0x1000,a,b);terminal(x,a,b,PageFailure::invalid);}
  } else if(name=="bounds") {
    for(int i=0;i<4;++i){File a;Pages b;if(i==0)a.value.file.inode=0;if(i==1)a.value.page.offset=1;if(i==2)b.value.offset=a.value.file.size;if(i==3)b.value.offset=UINT64_MAX;
      PageBinding x(0x1000,a,b);terminal(x,a,b,PageFailure::invalid);}
  } else if(name=="mismatch") {
    ++p.value.object;terminal(g,f,p,PageFailure::mismatch);
  } else if(name=="baseline_file"||name=="baseline_object"||name=="baseline_offset") {
    CHECK(g.sample().failure==PageFailure::none);
    if(name=="baseline_file")++f.value.file.inode;
    if(name=="baseline_object"){++f.value.page.object;++p.value.object;}
    if(name=="baseline_offset")++p.value.offset;
    terminal(g,f,p,PageFailure::changed);
  } else if(name=="lose_empty"||name=="lose_ready") {
    if(name=="lose_ready")CHECK(g.sample().failure==PageFailure::none);
    const int calls=f.calls+p.calls;g.lose();terminal(g,f,p,PageFailure::lost);CHECK(f.calls+p.calls==calls);
  } else CHECK(false);
}
}
int main(int argc,char** argv){CHECK(argc==2);test(argv[1]);}
