#include "sh3_observer/artifact_manifest.hpp"
#include "check.hpp"
#include <cstring>
using namespace sh3::observer;
namespace {
Sha256 sha() { Sha256 d{}; d[0]=7; return d; }
FileObject object() { return {1,2,65539,3,4,5,6}; }
struct Identity final : FileIdentitySource {
  FileObject value=object(); int calls{},fail_at{},change_at{};
  bool read(FileObject& out) noexcept override {
    ++calls;out=value;if(calls==change_at)++out.inode;return calls!=fail_at;
  }
};
struct Bytes final : ByteSource {
  std::uint64_t length=65539;int calls{},fail_at{},short_at{},long_at{};bool extra{};
  bool read_at(std::uint64_t offset,void* out,std::size_t wanted,std::size_t& got) noexcept override {
    ++calls;CHECK(wanted<=digest_block_size);CHECK(offset<=length);
    got=offset==length ? (extra ? 1 : 0) : wanted;
    if(calls==short_at)--got;if(calls==long_at)++got;
    std::memset(out,7,wanted);return calls!=fail_at;
  }
};
struct Hash final : DigestEngine {
  Sha256 value=sha();int starts{},updates{},ends{},bad{};std::size_t bytes{};
  bool begin() noexcept override {++starts;bytes=0;return bad!=1;}
  bool update(const void* p,std::size_t n) noexcept override {CHECK(p);++updates;bytes+=n;return bad!=2;}
  bool finish(Sha256& out) noexcept override {++ends;out=value;return bad!=3;}
};
void terminal(AnchoredDigest& d,Identity& i,Bytes& b,Hash& h,ManifestFailure expected) {
  FileDigest out{};CHECK(d.sample(out)==expected);CHECK(out.object.inode==0);CHECK(out.sha256==Sha256{});
  const int calls=i.calls+b.calls+h.starts+h.updates+h.ends;
  i.fail_at=0;b.fail_at=0;h.bad=0;
  CHECK(d.sample(out)==expected);d.lose();CHECK(d.sample(out)==expected);
  CHECK(calls==i.calls+b.calls+h.starts+h.updates+h.ends);
}
void digest(const char* scenario) {
  Identity i;Bytes b;Hash h;AnchoredDigest d(i,b,h);FileDigest out{};
  if(!std::strcmp(scenario,"digest_stable")) {
    CHECK(d.sample(out)==ManifestFailure::none);CHECK(out.sha256==sha());CHECK(b.calls==3);CHECK(h.bytes==65539);
    CHECK(d.sample(out)==ManifestFailure::none);CHECK(h.starts==2);
    d.lose();terminal(d,i,b,h,ManifestFailure::lost);
  } else if(!std::strcmp(scenario,"digest_identity_error")) {
    for(int n=1;n<=2;++n){Identity x;Bytes y;Hash z;x.fail_at=n;AnchoredDigest one(x,y,z);terminal(one,x,y,z,ManifestFailure::unavailable);}
  } else if(!std::strcmp(scenario,"digest_read_error")) {
    for(int n=1;n<=3;++n){Identity x;Bytes y;Hash z;y.fail_at=n;AnchoredDigest one(x,y,z);terminal(one,x,y,z,ManifestFailure::unavailable);}
  } else if(!std::strcmp(scenario,"digest_short")) {
    b.short_at=1;terminal(d,i,b,h,ManifestFailure::unavailable);
  } else if(!std::strcmp(scenario,"digest_long")) {
    b.long_at=1;terminal(d,i,b,h,ManifestFailure::unavailable);
  } else if(!std::strcmp(scenario,"digest_extra")) {
    b.extra=true;terminal(d,i,b,h,ManifestFailure::unavailable);
  } else if(!std::strcmp(scenario,"digest_hash_error")) {
    for(int n=1;n<=3;++n){Identity x;Bytes y;Hash z;z.bad=n;AnchoredDigest one(x,y,z);terminal(one,x,y,z,ManifestFailure::unavailable);}
  } else if(!std::strcmp(scenario,"digest_zero_hash")) {
    h.value={};terminal(d,i,b,h,ManifestFailure::invalid);
  } else if(!std::strcmp(scenario,"digest_invalid")) {
    for(int n=0;n<3;++n){Identity x;Bytes y;Hash z;x.value.size=n==0?0:artifact_file_limit+1;if(n==2)x.value.inode=0;AnchoredDigest one(x,y,z);terminal(one,x,y,z,ManifestFailure::invalid);CHECK(y.calls==0);}
  } else if(!std::strcmp(scenario,"digest_changed")) {
    i.change_at=2;terminal(d,i,b,h,ManifestFailure::changed);
  } else if(!std::strcmp(scenario,"digest_baseline_object")) {
    CHECK(d.sample(out)==ManifestFailure::none);++i.value.inode;terminal(d,i,b,h,ManifestFailure::changed);
  } else if(!std::strcmp(scenario,"digest_baseline_bytes")) {
    CHECK(d.sample(out)==ManifestFailure::none);++h.value[0];terminal(d,i,b,h,ManifestFailure::changed);
  } else if(!std::strcmp(scenario,"digest_lose")) {
    d.lose();terminal(d,i,b,h,ManifestFailure::lost);CHECK(i.calls==0);
  } else CHECK(false);
}
std::vector<ExpectedFile> expected() { return {{"a",65539,sha()},{"dir/b",65539,sha()}}; }
struct Source final : ArtifactSource {
  int calls{},bad_at{},change_at{},digest_at{},size_at{},invalid_at{};bool persistent{};
  bool read(std::string_view name,FileDigest& out) noexcept override {
    ++calls;out={object(),sha()};out.object.inode=name=="a"?10:20;
    if(calls==change_at||persistent)++out.object.inode;
    if(calls==digest_at)++out.sha256[0];if(calls==size_at)++out.object.size;
    if(calls==invalid_at)out.object.inode=0;
    return calls!=bad_at;
  }
};
void discarded(ManifestGuard& g,Source& s,ManifestFailure expected) {
  auto r=g.sample();CHECK(r.failure==expected);CHECK(r.count==0);CHECK(r.files[0].object.inode==0);
  int calls=s.calls;s.bad_at=0;s.persistent=false;CHECK(g.sample().failure==expected);g.lose();CHECK(g.sample().failure==expected);CHECK(calls==s.calls);
}
void manifest(const char* scenario) {
  Source s;auto config=expected();ManifestGuard g(config,s);
  if(!std::strcmp(scenario,"manifest_stable")) {
    config[0].name="modified caller copy";
    auto r=g.sample();CHECK(r.failure==ManifestFailure::none);CHECK(r.count==2);CHECK(s.calls==4);
    CHECK(g.sample().failure==ManifestFailure::none);g.lose();discarded(g,s,ManifestFailure::lost);
  } else if(!std::strcmp(scenario,"manifest_error")) {
    for(int n=1;n<=4;++n){Source x;x.bad_at=n;ManifestGuard one(expected(),x);discarded(one,x,ManifestFailure::unavailable);}
  } else if(!std::strcmp(scenario,"manifest_hash")) {
    for(int n=1;n<=4;++n){Source x;x.digest_at=n;ManifestGuard one(expected(),x);discarded(one,x,ManifestFailure::mismatch);}
  } else if(!std::strcmp(scenario,"manifest_size")) {
    s.size_at=1;discarded(g,s,ManifestFailure::mismatch);
  } else if(!std::strcmp(scenario,"manifest_invalid_read")) {
    s.invalid_at=1;discarded(g,s,ManifestFailure::invalid);
  } else if(!std::strcmp(scenario,"manifest_changed")) {
    for(int n=1;n<=4;++n){Source x;x.change_at=n;ManifestGuard one(expected(),x);discarded(one,x,ManifestFailure::changed);}
  } else if(!std::strcmp(scenario,"manifest_baseline")) {
    CHECK(g.sample().failure==ManifestFailure::none);s.persistent=true;discarded(g,s,ManifestFailure::changed);
  } else if(!std::strcmp(scenario,"manifest_lose")) {
    g.lose();discarded(g,s,ManifestFailure::lost);CHECK(s.calls==0);
  } else if(!std::strcmp(scenario,"manifest_config")) {
    for(int n=0;n<9;++n){auto c=expected();
      if(n==0)c.clear();if(n==1)c.resize(257);if(n==2)c[1].name=c[0].name;
      if(n==3)c[0].name="z";if(n==4)c[0].size=0;if(n==5)c[0].size=artifact_file_limit+1;
      if(n==6)c[0].sha256={};if(n==7)c[0].name="../a";
      if(n==8){c[0].size=c[1].size=artifact_file_limit;c.push_back({"z",1,sha()});}
      Source x;ManifestGuard one(c,x);discarded(one,x,ManifestFailure::invalid);CHECK(x.calls==0);
    }
    auto boundary=expected();boundary[0].size=boundary[1].size=artifact_file_limit;CHECK(valid_manifest(boundary));
  } else CHECK(false);
}
void paths() {
  for(const auto& name: {"", "/a", "a/", "a//b", "a/./b", "a/../b", ".", "..", "a\\b", "a:b", "a\nb"})CHECK(!valid_artifact_name(name));
  CHECK(!valid_artifact_name(std::string("a\0b",3)));CHECK(!valid_artifact_name(std::string(1,'\x80')));
  CHECK(!valid_artifact_name(std::string(256,'a')));CHECK(!valid_artifact_name(std::string(1025,'a')));
  CHECK(valid_artifact_name("Contents/Frameworks/libQt6Core.6.dylib"));CHECK(valid_artifact_name("dir/a name+1@2"));
}
}
int main(int argc,char** argv) {
  CHECK(argc==2);
  if(!std::strncmp(argv[1],"digest_",7))digest(argv[1]);else if(!std::strcmp(argv[1],"paths"))paths();else manifest(argv[1]);
}
