#include "launch_manifest_fixture.hpp"
#include "check.hpp"
#include <string>
using namespace sh3::observer;
using namespace launch_fixture;
namespace {
void bad(const LaunchManifest& m){CHECK(!valid_launch_manifest(m)&&launch_expected_files(m).empty());auto b=encode(m);LaunchManifest out=manifest();CHECK(decode_launch_manifest(b.data(),b.size(),out)!=LaunchFailure::none&&out.files.empty()&&out.roots.empty());}
void test(const std::string& n){
  auto m=manifest();auto b=encode(m);LaunchManifest out;
  if(n=="valid"){
    CHECK(valid_launch_manifest(m));CHECK(decode_launch_manifest(b.data(),b.size(),out)==LaunchFailure::none);
    CHECK(out.roots==m.roots&&out.files.size()==2&&out.files[1].file.name=="y"&&out.files[1].file.size==128&&out.cache==m.cache);
    auto files=launch_expected_files(out);CHECK(valid_manifest(files)&&files[0].name=="0/x"&&files[1].name=="1/y");
  }else if(n=="header"){
    for(unsigned mode=0;mode<8;++mode){auto bytes=b;
      if(mode==0)bytes[7]='2';if(mode==1)word(bytes,8,0);if(mode==2)word(bytes,8,9);if(mode==3)word(bytes,12,0);
      if(mode==4)word(bytes,12,257);if(mode==5)word(bytes,16,2);if(mode==6)word(bytes,100,UINT32_MAX);if(mode==7)bytes.push_back(0);
      CHECK(decode_launch_manifest(bytes.data(),bytes.size(),out)==LaunchFailure::malformed&&out.files.empty());
    }
    CHECK(decode_launch_manifest(nullptr,100,out)==LaunchFailure::invalid);
    CHECK(decode_launch_manifest(b.data(),launch_manifest_limit+1,out)==LaunchFailure::invalid);
  }else if(n=="truncated"){
    for(std::size_t size=0;size<b.size();++size)CHECK(decode_launch_manifest(b.data(),size,out)!=LaunchFailure::none&&out.files.empty());
  }else if(n=="roots"){
    for(const auto& root:{std::string{},std::string("/"),std::string("relative"),std::string("/x/../y"),std::string("/x//y"),std::string("/x\\y"),std::string("/x\0y",4),std::string("/b")}){auto x=m;x.roots[0]=root;bad(x);}
    auto x=m;x.roots.push_back("/unused");bad(x);x=m;x.roots.clear();bad(x);
  }else if(n=="files"){
    for(unsigned mode=0;mode<12;++mode){auto x=m;
      if(mode==0)x.files[0].root=2;if(mode==1)x.files[0].file.name="../x";if(mode==2)x.files[0].file.name="";
      if(mode==3)x.files[0].file.size=0;if(mode==4)x.files[0].file.size=artifact_file_limit+1;
      if(mode==5)x.files[0].file.sha256={};if(mode==6)std::swap(x.files[0],x.files[1]);
      if(mode==7)x.files[1]=x.files[0];if(mode==8)x.cache={};if(mode==9)x.policy_evidence={};
      if(mode==10)x.platform_evidence={};if(mode==11)x.main_file=2;bad(x);
    }
    auto x=m;x.roots={"/a"};x.files={{0,{"a",artifact_file_limit,tag(1)}},{0,{"b",artifact_file_limit,tag(2)}},{0,{"c",1,tag(3)}}};bad(x);
  }else if(n=="capacity"){
    m.files.clear();m.roots.clear();for(unsigned root=0;root<8;++root){m.roots.push_back("/r"+std::to_string(root));for(unsigned f=0;f<32;++f)m.files.push_back({root,{std::to_string(1000+f),64,tag(1)}});}
    CHECK(valid_launch_manifest(m));auto bytes=encode(m);CHECK(decode_launch_manifest(bytes.data(),bytes.size(),out)==LaunchFailure::none&&out.files.size()==256);
    m.files.push_back({7,{"z",64,tag(1)}});bad(m);
  }else if(n=="read"){
    Source source(b);Hash hash;CHECK(read_launch_manifest(source,source,hash,digest(b),out)==LaunchFailure::none&&source.identities==2&&out.files.size()==2);
    auto large=manifest();large.files.clear();large.roots={"/a"};
    for(unsigned i=0;i<256;++i){std::string name=std::to_string(1000+i)+"/"+std::string(250,'x');large.files.push_back({0,{name,64,tag(1)}});}
    auto bytes=encode(large);Source blocks(bytes);CHECK(read_launch_manifest(blocks,blocks,hash,digest(bytes),out)==LaunchFailure::none&&hash.calls>1);
  }else if(n=="read_failures"){
    for(unsigned mode=0;mode<10;++mode){Source source(b);Hash hash;auto expected=digest(b);
      if(mode==0)source.fail_at=1;if(mode==1)source.short_at=1;if(mode==2)source.fail_at=2;
      if(mode==3)source.extra=true;if(mode==4)source.change_at=2;if(mode==5)expected[0]^=1;
      if(mode==6)expected={};if(mode==7)source.declared=99;if(mode==8)source.declared=launch_manifest_limit+1;if(mode==9)source.change_at=1;
      CHECK(read_launch_manifest(source,source,hash,expected,out)!=LaunchFailure::none&&out.files.empty());
    }
  }else if(n=="hash_failures"){
    for(int fail=1;fail<=3;++fail){Source source(b);Hash hash;hash.fail=fail;CHECK(read_launch_manifest(source,source,hash,digest(b),out)==LaunchFailure::unavailable&&out.files.empty());}
  }else CHECK(false);
}
}
int main(int argc,char** argv){CHECK(argc==2);test(argv[1]);}
