#include "sh3_observer/cache_range.hpp"
#include "check.hpp"
#include <algorithm>
#include <cstring>
#include <limits>
using namespace sh3::observer;
namespace {
Sha256 sha(){Sha256 s{};s[0]=42;return s;}
FileObject object(){return {1,2,65536,3,4,5,6};}
struct File final : PageFileSource {
  PageFileReading value{object(),{77,0,true,true,false}};
  int calls{},fail_at{},change_at{},object_at{},invalid_at{};
  bool read(PageFileReading& out) noexcept override {
    ++calls;out=value;
    if(calls==change_at)++out.file.inode;
    if(calls==object_at)++out.page.object;
    if(calls==invalid_at)out.page.modified=true;
    return calls!=fail_at;
  }
};
struct Pages final : PageSource {
  int calls{},fail_at{},dirty_at{},object_at{},offset_at{};
  std::vector<std::uintptr_t> addresses;
  bool read(std::uintptr_t address,PageReading& out) noexcept override {
    ++calls;addresses.push_back(address);out={77,address-0x10000,true,true,false};
    if(calls==dirty_at)out.modified=true;
    if(calls==object_at)++out.object;
    if(calls==offset_at)++out.offset;
    return calls!=fail_at;
  }
};
std::vector<CacheRange> ranges(){return {{0x10000,12288,0}};}
void terminal(CacheRangeGuard& g,File& f,Pages& p,PageFailure expected){
  auto out=g.sample();CHECK(out.failure==expected);CHECK(out.pages==0&&out.bytes==0&&out.object==0);
  CHECK(out.file.object.inode==0&&out.file.sha256==Sha256{});
  const auto calls=f.calls+p.calls;
  f.fail_at=p.fail_at=0;g.lose();CHECK(g.sample().failure==expected);CHECK(f.calls+p.calls==calls);
}
void range_test(const std::string& name){
  File f;Pages p;CacheRangeGuard g({object(),sha()},ranges(),4096,f,p);
  if(name=="stable"){
    auto r=g.sample();CHECK(r.failure==PageFailure::none&&r.pages==3&&r.bytes==12288&&r.object==77);
    CHECK(r.file.sha256==sha());CHECK(p.addresses==std::vector<std::uintptr_t>({0x10000,0x11000,0x12000,0x10000,0x11000,0x12000}));
    CHECK(f.calls==4);CHECK(g.sample().failure==PageFailure::none);g.lose();terminal(g,f,p,PageFailure::lost);
  }else if(name=="partial"){
    auto cfg=std::vector<CacheRange>{{0x10003,8192,3},{0x14000,1,16384}};
    CacheRangeGuard one({object(),sha()},cfg,4096,f,p);cfg[0].address=0;
    auto r=one.sample();CHECK(r.failure==PageFailure::none&&r.pages==4&&r.bytes==8193);
    CHECK(p.addresses==std::vector<std::uintptr_t>({0x10003,0x11000,0x12000,0x14000,0x10003,0x11000,0x12000,0x14000}));
  }else if(name=="page16k"){
    CacheRangeGuard one({object(),sha()},{{0x10003,16384,3}},16384,f,p);
    auto r=one.sample();CHECK(r.failure==PageFailure::none&&r.pages==2&&r.bytes==16384);
    CHECK(p.addresses==std::vector<std::uintptr_t>({0x10003,0x14000,0x10003,0x14000}));
  }else if(name=="page_errors"){
    for(int kind=0;kind<4;++kind)for(int n=1;n<=6;++n){File x;Pages y;
      if(kind==0)y.fail_at=n;if(kind==1)y.dirty_at=n;if(kind==2)y.object_at=n;if(kind==3)y.offset_at=n;
      CacheRangeGuard one({object(),sha()},ranges(),4096,x,y);
      terminal(one,x,y,kind==0?PageFailure::unavailable:(kind==1?PageFailure::invalid:PageFailure::mismatch));
    }
  }else if(name=="reference_errors"){
    for(int kind=0;kind<4;++kind)for(int n=1;n<=4;++n){File x;Pages y;
      if(kind==0)x.fail_at=n;if(kind==1)x.change_at=n;if(kind==2)x.object_at=n;if(kind==3)x.invalid_at=n;
      CacheRangeGuard one({object(),sha()},ranges(),4096,x,y);
      terminal(one,x,y,kind==0?PageFailure::unavailable:(kind==3?PageFailure::invalid:(kind==2&&n==1?PageFailure::mismatch:PageFailure::changed)));
    }
  }else if(name=="reference_invalid"){
    for(int n=0;n<7;++n){File x;Pages y;
      if(n==0)x.value.page.offset=1;if(n==1)x.value.page.resident=false;if(n==2)x.value.page.external=false;
      if(n==3)x.value.page.object=0;if(n==4)x.value.page.modified=true;if(n==5)x.value.file.inode=0;if(n==6)x.value.file.size++;
      CacheRangeGuard one({object(),sha()},ranges(),4096,x,y);terminal(one,x,y,n==6?PageFailure::changed:PageFailure::invalid);
    }
  }else if(name=="configuration"){
    for(int n=0;n<17;++n){File x;Pages y;auto c=ranges();FileDigest d{object(),sha()};std::uint64_t page=4096;
      if(n==0)c.clear();if(n==1)c.resize(cache_range_capacity+1);
      if(n==2)c[0].address=0;if(n==3)c[0].size=0;if(n==4)c[0].address=std::numeric_limits<std::uintptr_t>::max()-100;
      if(n==5)c[0].offset=d.object.size+1;if(n==6)c[0].size=d.object.size+1;if(n==7)c[0].offset=1;
      if(n==8)c.push_back({0x11000,4096,4096});if(n==9)c={{0x12000,4096,8192},{0x10000,4096,0}};
      if(n==10)d.object.inode=0;if(n==11)d.object.size=cache_file_limit+1;if(n==12)d.sha256={};
      if(n==13)page=0;if(n==14)page=8192;
      if(n==15){c.clear();d.object.size=cache_file_limit;for(unsigned k=0;k<9;++k)c.push_back({0x10000+k*cache_file_limit,cache_file_limit,0});}
      if(n==16)c[0].offset=d.object.size;
      CacheRangeGuard one(d,c,page,x,y);terminal(one,x,y,PageFailure::invalid);CHECK(x.calls==0&&y.calls==0);
    }
    std::vector<CacheRange> c;for(std::size_t n=0;n<cache_range_capacity;++n)c.push_back({0x10000+n*4096,1,0});
    p.fail_at=1;CacheRangeGuard capacity({object(),sha()},c,4096,f,p);terminal(capacity,f,p,PageFailure::unavailable);
    File x;Pages y;y.fail_at=1;c.clear();auto d=FileDigest{object(),sha()};d.object.size=cache_file_limit;x.value.file=d.object;
    for(unsigned k=0;k<8;++k)c.push_back({0x10000+k*cache_file_limit,cache_file_limit,0});
    CacheRangeGuard budget(d,c,4096,x,y);terminal(budget,x,y,PageFailure::unavailable);
  }else if(name=="baseline"){
    CHECK(g.sample().failure==PageFailure::none);++f.value.page.object;terminal(g,f,p,PageFailure::changed);
  }else if(name=="lose"){
    g.lose();terminal(g,f,p,PageFailure::lost);CHECK(f.calls==0&&p.calls==0);
  }else CHECK(false);
}
struct Large final : FileIdentitySource,ByteSource,DigestEngine {
  std::uint64_t length=artifact_file_limit+1,consumed{},next{};int reads{},starts{};
  bool read(FileObject& out) noexcept override{out=object();out.size=length;return true;}
  bool read_at(std::uint64_t off,void* bytes,std::size_t n,std::size_t& got) noexcept override{
    CHECK(off==next&&bytes&&n<=digest_block_size);++reads;got=off==length?0:n;next+=got;return true;
  }
  bool begin() noexcept override{++starts;consumed=next=0;return true;}
  bool update(const void*,std::size_t n) noexcept override{consumed+=n;return true;}
  bool finish(Sha256& out) noexcept override{out=sha();return true;}
};
struct Source final : ArtifactSource {
  int calls{};bool wrong{};
  bool read(std::string_view,FileDigest& out) noexcept override{++calls;out={object(),sha()};out.object.size=artifact_file_limit+1;if(wrong)++out.sha256[0];return true;}
};
void policy(const std::string& name){
  if(name=="domain_digest"){
    for(auto domain:{ArtifactDomain::bundle,ArtifactDomain::system_cache,static_cast<ArtifactDomain>(99)}){
      Large x;AnchoredDigest g(x,x,x,domain);FileDigest out{};
      CHECK(g.sample(out)==(domain==ArtifactDomain::system_cache?ManifestFailure::none:ManifestFailure::invalid));
      if(domain==ArtifactDomain::system_cache){CHECK(x.consumed==x.length&&x.reads==4098);CHECK(g.sample(out)==ManifestFailure::none);}
      else CHECK(x.reads==0&&x.starts==0);
    }
    Large x;x.length=cache_file_limit;AnchoredDigest g(x,x,x,ArtifactDomain::system_cache);FileDigest out{};
    CHECK(g.sample(out)==ManifestFailure::none&&x.consumed==cache_file_limit);
    Large y;y.length=cache_file_limit+1;AnchoredDigest bad(y,y,y,ArtifactDomain::system_cache);
    CHECK(bad.sample(out)==ManifestFailure::invalid&&y.reads==0);
  }else if(name=="domain_manifest"){
    std::vector<ExpectedFile> cfg{{"cache",artifact_file_limit+1,sha()}};
    CHECK(!valid_manifest(cfg)&&valid_manifest(cfg,ArtifactDomain::system_cache));
    Source x;ManifestGuard g(cfg,x,ArtifactDomain::system_cache);cfg[0].sha256={};
    CHECK(g.sample().failure==ManifestFailure::none&&x.calls==2);x.wrong=true;
    CHECK(g.sample().failure==ManifestFailure::mismatch);int calls=x.calls;x.wrong=false;
    CHECK(g.sample().failure==ManifestFailure::mismatch&&x.calls==calls);
    Source y;ManifestGuard old({{"cache",artifact_file_limit+1,sha()}},y);
    CHECK(old.sample().failure==ManifestFailure::invalid&&y.calls==0);
  }else if(name=="domain_limits"){
    for(int n=0;n<8;++n){std::vector<ExpectedFile> c{{"a",1,sha()}};auto domain=ArtifactDomain::system_cache;
      if(n==0)c[0].size=cache_file_limit+1;if(n==1)c[0].size=0;if(n==2)c[0].sha256={};
      if(n==3)c[0].name="/a";if(n==4)c.clear();if(n==5)domain=static_cast<ArtifactDomain>(99);
      if(n==6||n==7){c.clear();for(int k=0;k<(n==6?33:9);++k)c.push_back({std::to_string(100+k),n==6?1:cache_file_limit,sha()});}
      CHECK(!valid_manifest(c,domain));
    }
    std::vector<ExpectedFile> c;for(int n=0;n<32;++n)c.push_back({std::to_string(100+n),1,sha()});CHECK(valid_manifest(c,ArtifactDomain::system_cache));
    c.clear();for(int n=0;n<8;++n)c.push_back({std::to_string(100+n),cache_file_limit,sha()});CHECK(valid_manifest(c,ArtifactDomain::system_cache));
    CHECK(artifact_file_limit==256ULL*1024*1024&&artifact_total_limit==512ULL*1024*1024);
  }else CHECK(false);
}
}
int main(int argc,char** argv){CHECK(argc==2);std::string name=argv[1];if(name.rfind("domain_",0)==0)policy(name);else range_test(name);}
