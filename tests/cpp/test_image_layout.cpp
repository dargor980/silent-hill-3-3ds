#include "sh3_observer/image_layout.hpp"
#include "image_layout_fixture.hpp"
#include "check.hpp"
#include <cstring>
#include <limits>
#include <string>
using namespace sh3::observer;
using namespace layout_fixture;
namespace {
constexpr auto text_segment=32+72;
struct Source final : ByteSource {
  Bytes data=valid();int calls{},fail_at{},short_at{},long_at{},change_at{};std::size_t maximum{};std::uint64_t total{};
  bool read_at(std::uint64_t offset,void* out,std::size_t wanted,std::size_t& got) noexcept override{
    ++calls;maximum=std::max(maximum,wanted);CHECK(wanted<=digest_block_size);CHECK(offset<=data.size()&&wanted<=data.size()-offset);
    std::memcpy(out,data.data()+offset,wanted);got=wanted;total+=got;
    if(calls==short_at)--got;if(calls==long_at)++got;
    if(calls==change_at)static_cast<unsigned char*>(out)[wanted-1]^=1;
    return calls!=fail_at;
  }
};
void rejected(Bytes bytes,LayoutFailure expected){ImageLayout out{};out.count=99;out.header_address=99;CHECK(parse_image_layout(bytes.data(),bytes.size(),out)==expected);CHECK(out.count==0&&out.header_address==0&&out.cpu==0);}
void test(const std::string& name){
  auto b=valid();ImageLayout out{};
  if(name=="valid"){
    CHECK(parse_image_layout(b.data(),b.size(),out)==LayoutFailure::none);CHECK(out.count==3&&out.commands==4&&out.flags==0x80000000);
    CHECK(out.header_address==0x100000000&&out.segments[2].size-out.segments[2].file_size==12288);
    CHECK(out.segments[1].sections==1&&out.segments[1].flags==4);
    CHECK(out.segments[2].maximum_protection==3&&out.segments[2].initial_protection==3);
  }else if(name=="architectures"){
    for(auto cpu:{0x01000007U,0x0100000cU})for(auto type:{2U,6U,7U,8U}){put32(b,4,cpu);put32(b,12,type);CHECK(parse_image_layout(b.data(),b.size(),out)==LayoutFailure::none);}
  }else if(name=="unsupported"){
    for(int n=0;n<4;++n){auto x=b;if(n==0)put32(x,0,0xcffaedfe);if(n==1)put32(x,4,7);if(n==2)put32(x,12,1);if(n==3)put32(x,32,1);rejected(x,LayoutFailure::unsupported);}
  }else if(name=="header_limits"){
    for(int n=0;n<8;++n){auto x=b;if(n==0)x.resize(31);if(n==1)put32(x,28,1);if(n==2)put32(x,16,0);if(n==3)put32(x,16,4097);if(n==4)put32(x,20,layout_command_limit+8);if(n==5)put32(x,20,9);if(n==6)put32(x,20,8);if(n==7)x.push_back(0);rejected(x,LayoutFailure::invalid);}
    CHECK(parse_image_layout(nullptr,0,out)==LayoutFailure::invalid);
  }else if(name=="commands"){
    for(int n=0;n<5;++n){auto x=b;if(n==0)put32(x,36,0);if(n==1)put32(x,36,9);if(n==2)put32(x,36,0xfffffff8);if(n==3)put32(x,16,3);if(n==4)put32(x,16,5);rejected(x,LayoutFailure::invalid);}
  }else if(name=="sections"){
    auto x=b;put32(x,text_segment+64,0xffffffff);rejected(x,LayoutFailure::invalid);
    x=b;put32(x,text_segment+4,64);rejected(x,LayoutFailure::invalid);
  }else if(name=="names"){
    for(int n=0;n<4;++n){auto x=b;if(n==0)x[40]=0;if(n==1)x[41]=1;if(n==2)x[41]=255;if(n==3)x[47]=0;rejected(x,LayoutFailure::invalid);}
    auto x=b;std::memset(x.data()+40,'a',16);CHECK(parse_image_layout(x.data(),x.size(),out)==LayoutFailure::none);
  }else if(name=="segment_ranges"){
    for(int n=0;n<4;++n){auto x=b;if(n==0)put64(x,text_segment+48,16385);if(n==1)put64(x,text_segment+24,UINT64_MAX-100);if(n==2)put64(x,text_segment+40,UINT64_MAX-100);if(n==3)put64(x,text_segment+24,4096);rejected(x,LayoutFailure::invalid);}
  }else if(name=="protections"){
    for(int n=0;n<3;++n){auto x=b;if(n==0)put32(x,text_segment+56,8);if(n==1)put32(x,text_segment+60,8);if(n==2)put32(x,text_segment+56,1);rejected(x,LayoutFailure::invalid);}
  }else if(name=="text"){
    for(int n=0;n<4;++n){auto x=b;if(n==0)x[text_segment+8]='A';if(n==1)std::memcpy(x.data()+40,"__TEXT\0\0\0\0\0\0\0\0\0\0",16);if(n==2)put64(x,text_segment+48,32);if(n==3)put32(x,text_segment+60,4);rejected(x,LayoutFailure::invalid);}
  }else if(name=="empty_segment"){
    put64(b,64,0);CHECK(parse_image_layout(b.data(),b.size(),out)==LayoutFailure::none);CHECK(out.count==3&&out.segments[0].size==0);
  }else if(name=="segment_capacity"){
    b.resize(32);segment(b,"__TEXT",0x10000,65536,0,65536,5);
    for(std::size_t i=1;i<layout_segment_capacity;++i)segment(b,"__EMPTY",0,0,0,0,0);
    put32(b,16,layout_segment_capacity);put32(b,20,b.size()-32);CHECK(parse_image_layout(b.data(),b.size(),out)==LayoutFailure::none&&out.count==layout_segment_capacity);
    segment(b,"__EMPTY",0,0,0,0,0);put32(b,16,layout_segment_capacity+1);put32(b,20,b.size()-32);rejected(b,LayoutFailure::invalid);
    static_assert(image_capacity==2048&&artifact_file_capacity==256&&cache_file_capacity==32);
  }else if(name=="capacity_domains"){
    Sha256 hash{};hash[0]=1;std::vector<ExpectedFile> files;
    for(unsigned i=0;i<artifact_file_capacity;++i)files.push_back({std::to_string(1000+i),1,hash});
    CHECK(valid_manifest(files));files.push_back({"2000",1,hash});CHECK(!valid_manifest(files));
    CHECK(image_capacity==2048&&files.size()==257);
  }else if(name=="read_stable"){
    Source s;CHECK(read_image_layout(s,out)==LayoutFailure::none&&out.count==3);CHECK(s.calls==3&&s.total==32+2*b.size());
  }else if(name=="read_failures"){
    for(int kind=0;kind<3;++kind)for(int n=1;n<=3;++n){Source s;if(kind==0)s.fail_at=n;if(kind==1)s.short_at=n;if(kind==2)s.long_at=n;out.count=99;CHECK(read_image_layout(s,out)==LayoutFailure::unavailable&&out.count==0);}
    Source s;s.data[0]=0;CHECK(read_image_layout(s,out)==LayoutFailure::unsupported&&s.calls==1);
  }else if(name=="read_changed"){
    for(int n=2;n<=3;++n){Source s;s.change_at=n;CHECK(read_image_layout(s,out)==LayoutFailure::changed&&out.count==0);}
    Source s;s.change_at=1;CHECK(read_image_layout(s,out)==LayoutFailure::invalid);
  }else if(name=="read_blocks"){
    Source s;s.data.resize(32);segment(s.data,"__TEXT",0x10000,2*layout_command_limit,0,2*layout_command_limit,5);
    auto p=s.data.size();s.data.resize(32+layout_command_limit);put32(s.data,p,0x9876);put32(s.data,p+4,s.data.size()-p);put32(s.data,16,2);put32(s.data,20,layout_command_limit);
    CHECK(read_image_layout(s,out)==LayoutFailure::none&&out.count==1);CHECK(s.maximum==digest_block_size&&s.calls==35);
  }else CHECK(false);
}
}
int main(int argc,char** argv){CHECK(argc==2);test(argv[1]);}
