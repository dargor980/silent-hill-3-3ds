#include "sh3_observer/image_identity.hpp"
#include "check.hpp"
#include <cstring>
#include <limits>
using namespace sh3::observer;
namespace {
FileObject good() { return {7, 21, 8192, 40, 41, 22, 23}; }
struct File final : FileIdentitySource {
  FileObject value = good();
  int calls{}, fail_at{}, change_at{};
  bool read(FileObject& out) noexcept override {
    ++calls; out = value;
    if (calls == change_at) ++out.inode;
    return calls != fail_at;
  }
};
struct Map final : MappingSource {
  MappedFile value{4096, 4096, 0, good()};
  int calls{}, fail_at{}, change_at{};
  bool read(std::uintptr_t, MappedFile& out) noexcept override {
    ++calls; out = value;
    if (calls == change_at) ++out.file.inode;
    return calls != fail_at;
  }
};
void terminal(ImageBinding& b, File& f, Map& m, ImageFailure reason) {
  const auto r = b.sample();
  CHECK(r.failure == reason); CHECK(r.mapping.address == 0); CHECK(r.mapping.file.inode == 0);
  f = File{}; m = Map{};
  CHECK(b.sample().failure == reason); CHECK(f.calls + m.calls == 0);
  b.lose(); CHECK(b.sample().failure == reason);
}
void binding(const char* scenario) {
  File f; Map m; ImageBinding b(4096, f, m);
  if (!std::strcmp(scenario, "stable")) {
    for (int i=0; i<100; ++i) { auto r=b.sample(); CHECK(r.failure==ImageFailure::none); CHECK(same_file(r.mapping.file,good())); }
    b.lose(); terminal(b,f,m,ImageFailure::lost);
  } else if (!std::strcmp(scenario, "unavailable")) {
    for (int step=0; step<4; ++step) {
      File x; Map y; ImageBinding one(4096,x,y);
      if (step<2) x.fail_at=step+1; else y.fail_at=step-1;
      terminal(one,x,y,ImageFailure::unavailable);
    }
  } else if (!std::strcmp(scenario, "unstable")) {
    for (int step=0;step<4;++step) {
      File x; Map y; ImageBinding one(4096,x,y);
      if (step<2) x.change_at=step+1; else y.change_at=step-1;
      terminal(one,x,y,ImageFailure::changed);
    }
  } else if (!std::strcmp(scenario, "baseline")) {
    CHECK(b.sample().failure==ImageFailure::none);
    ++f.value.inode; ++m.value.file.inode;
    terminal(b,f,m,ImageFailure::changed);
  } else if (!std::strcmp(scenario, "mapping_changed")) {
    CHECK(b.sample().failure==ImageFailure::none);
    ++m.value.size;
    terminal(b,f,m,ImageFailure::changed);
  } else if (!std::strcmp(scenario, "invalid_mapping")) {
    for (int step=0;step<5;++step) {
      File x; Map y;
      if (step==0) y.value.address=8192;
      if (step==1) y.value.size=0;
      if (step==2) y.value.offset=1;
      if (step==3) y.value.size=UINT64_MAX;
      ImageBinding one(step==4 ? 0 : 4096,x,y);
      terminal(one,x,y,ImageFailure::invalid);
    }
  } else if (!std::strcmp(scenario, "invalid_file")) {
    for (int step=0;step<7;++step) {
      File x; Map y;
      if(step==0)x.value.device=0;
      if(step==1)x.value.inode=0;
      if(step==2)x.value.size=0;
      if(step==3)x.value.modified_seconds=-1;
      if(step==4)x.value.changed_seconds=-1;
      if(step==5)x.value.modified_ns=1000000000;
      if(step==6)x.value.changed_ns=1000000000;
      ImageBinding one(4096,x,y); terminal(one,x,y,ImageFailure::invalid);
    }
  } else if (!std::strcmp(scenario, "lose_empty")) {
    b.lose(); terminal(b,f,m,ImageFailure::lost);
  } else if (!std::strcmp(scenario,"file_equality")) {
    for(int step=0;step<7;++step) {
      auto a=good();
      if(step==0)++a.device;
      if(step==1)++a.inode;
      if(step==2)++a.size;
      if(step==3)++a.modified_seconds;
      if(step==4)++a.changed_seconds;
      if(step==5)++a.modified_ns;
      if(step==6)++a.changed_ns;
      CHECK(!same_file(a,good()));
    }
  } else CHECK(false);
}
void ledger(const char* scenario) {
  ImageLedger l; ImageSnapshot s{};
  if(!std::strcmp(scenario,"ledger_cycle")) {
    CHECK(l.read(s)); CHECK(s.count==0); CHECK(s.revision==1);
    l.add(11);l.add(22);l.add(33);
    CHECK(l.read(s)); CHECK(s.count==3); CHECK(s.revision==4);
    l.remove(22); CHECK(l.read(s)); CHECK(s.addresses[1]==33); CHECK(s.addresses[2]==0);
    l.add(22); CHECK(l.read(s)); CHECK(s.count==3); CHECK(s.revision==6);
    l.remove(22);l.remove(33);l.remove(11);
    CHECK(l.read(s)); CHECK(s.count==0); CHECK(s.revision==9);
  } else {
    if(!std::strcmp(scenario,"ledger_duplicate")){l.add(11);l.add(11);}
    else if(!std::strcmp(scenario,"ledger_unknown")){l.add(11);l.remove(22);}
    else if(!std::strcmp(scenario,"ledger_null"))l.add(0);
    else if(!std::strcmp(scenario,"ledger_capacity")){
      for(std::size_t i=1;i<=image_capacity;++i) l.add(i);
      CHECK(l.read(s)); CHECK(s.count==image_capacity);
      l.add(image_capacity+1);
    } else if(!std::strcmp(scenario,"ledger_exhaustion")){
      ImageLedger almost(UINT64_MAX-2); almost.add(11);CHECK(almost.read(s));
      CHECK(s.revision==UINT64_MAX-1); almost.remove(11);CHECK(!almost.read(s));CHECK(s.revision==0);
      ImageLedger last(UINT64_MAX-1);last.add(11);CHECK(!last.read(s));
      ImageLedger zero(0);CHECK(!zero.read(s));
      ImageLedger maximum(UINT64_MAX);CHECK(!maximum.read(s));
      return;
    } else CHECK(false);
    CHECK(!l.read(s)); CHECK(s.count==0); CHECK(s.revision==0);
    l.remove(11);l.add(22);CHECK(!l.read(s));CHECK(s.addresses[0]==0);
  }
}
}
int main(int argc,char** argv) {
  CHECK(argc==2);
  if(!std::strncmp(argv[1],"ledger_",7))ledger(argv[1]);else binding(argv[1]);
}
