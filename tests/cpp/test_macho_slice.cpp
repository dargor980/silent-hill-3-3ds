#include "macho_slice_fixture.hpp"
#include "check.hpp"
#include <string>
using namespace sh3::observer;
using namespace slice_fixture;
namespace {
void rejected(Bytes data,SliceFailure expected,SliceRequest wanted={0x1000007,3,4096}) {
  Source source(std::move(data));MachSlice out{};out.size=99;
  CHECK(select_macho_slice(source,source.bytes.size(),wanted,out)==expected&&same_slice(out,{}));
}
void test(const std::string& name) {
  if(name=="valid") {
    for(unsigned kind=0;kind<3;++kind){Source source(kind?fat(kind==2):thin());MachSlice out{};
      CHECK(select_macho_slice(source,source.bytes.size(),{0x1000007,3,kind?4096U:0U},out)==SliceFailure::none);
      CHECK(out.format==static_cast<SliceFormat>(kind+1)&&out.size==64&&out.offset==(kind?4096U:0U));
      if(kind){CHECK(select_macho_slice(source,source.bytes.size(),{0x100000c,0x80000002,8192},out)==SliceFailure::none);CHECK(out.offset==8192);}
    }
  }else if(name=="endian") {
    for(auto magic:{0xbebafecaU,0xbfbafecaU,0xfeedfacfU,0xcefaedfeU,0x12345678U}){auto b=fat();be32(b,0,magic);rejected(b,SliceFailure::unsupported);}
  }else if(name=="selection") {
    for(auto q:{SliceRequest{0x1000007,4,4096},SliceRequest{0x1000007,3,8192},SliceRequest{0x100000c,2,8192}})rejected(fat(),SliceFailure::missing,q);
    rejected(fat(),SliceFailure::unsupported,{7,3,4096});rejected(thin(),SliceFailure::missing,{0x1000007,3,1});
  }else if(name=="limits") {
    for(auto size:std::array<std::uint64_t,3>{0,31,artifact_file_limit+1}){Source source(thin());MachSlice out{};CHECK(select_macho_slice(source,size,{0x1000007,3,0},out)==SliceFailure::invalid&&source.calls==0);}
    Source source(thin());MachSlice out{};CHECK(select_macho_slice(source,64,{0x1000007,3,65},out)==SliceFailure::invalid);
    for(auto count:{0U,33U,UINT32_MAX}){auto b=fat();be32(b,4,count);rejected(b,SliceFailure::invalid);}
    Source full(fat(true,32));CHECK(select_macho_slice(full,full.bytes.size(),{0x1000007,3,4096},out)==SliceFailure::none);CHECK(full.requested==4112);
  }else if(name=="ranges") {
    for(unsigned mode=0;mode<9;++mode){auto b=fat(true);
      if(mode==0)be64(b,16,UINT64_MAX);if(mode==1)be64(b,24,UINT64_MAX);if(mode==2)be64(b,24,31);
      if(mode==3)be64(b,16,16);if(mode==4)be64(b,16,4097);if(mode==5)be32(b,32,64);
      if(mode==6)be32(b,36,1);if(mode==7)be64(b,24,b.size());
      if(mode==8){be32(b,32,0);be64(b,16,b.size());}
      rejected(b,SliceFailure::invalid);
    }
    auto b=fat(true);b.resize(40);rejected(b,SliceFailure::unavailable,{0x1000007,3,0});
  }else if(name=="overlap") {
    auto b=fat();const auto h=thin(0x100000c,0x80000002);std::copy(h.begin(),h.end(),b.begin()+4128);be32(b,36,4128);be32(b,44,5);rejected(b,SliceFailure::invalid);
  }else if(name=="ambiguous") {
    auto b=fat();be32(b,28,0x1000007);be32(b,32,3);le32(b,8192+4,0x1000007);le32(b,8192+8,3);rejected(b,SliceFailure::ambiguous);
  }else if(name=="headers") {
    for(unsigned mode=0;mode<10;++mode){auto b=fat();const auto p=8192;
      if(mode==0)le32(b,p,0);if(mode==1)le32(b,p+4,7);if(mode==2)le32(b,p+12,1);
      if(mode==3)le32(b,p+16,0);if(mode==4)le32(b,p+20,1024*1024+1);if(mode==5)le32(b,p+16,2);
      if(mode==6)le32(b,p+20,40);if(mode==7)le32(b,p+28,1);if(mode==8)le32(b,p+8,3);if(mode==9)be32(b,28,0x1000007);
      rejected(b,SliceFailure::invalid);
    }
    for(auto type:{2U,6U,8U}){Source source(thin());le32(source.bytes,12,type);MachSlice s{};CHECK(select_macho_slice(source,64,{0x1000007,3,0},s)==SliceFailure::none);}
  }else if(name=="reads") {
    for(int at=1;at<=8;++at)for(bool partial:{false,true}){Source source(fat());if(partial)source.short_at=at;else source.fail_at=at;MachSlice out{};CHECK(select_macho_slice(source,source.bytes.size(),{0x1000007,3,4096},out)==SliceFailure::unavailable&&same_slice(out,{}));}
  }else if(name=="changes") {
    for(auto index:{4096+24,8192+24}){Source source(fat());source.change_at=5;source.change_index=index;MachSlice out{};CHECK(select_macho_slice(source,source.bytes.size(),{0x1000007,3,4096},out)==SliceFailure::changed);}
    Source source(fat());source.change_at=5;source.change_index=27;source.bytes[27]=11;MachSlice out{};CHECK(select_macho_slice(source,source.bytes.size(),{0x1000007,3,4096},out)==SliceFailure::changed);
  }else if(name=="binding"||name=="binding_failures") {
    const unsigned cases=name=="binding"?1:15;
    for(unsigned mode=0;mode<cases;++mode){Source file(fat()),resident(thin());Identity identity(file.bytes.size());MappedFile mapping{0x1000,4096,4096,identity.value};SliceBinding out{};
      if(name=="binding_failures"){
        if(mode==0)mapping.address=0;if(mode==1)mapping.size=31;if(mode==2)mapping.size=UINT64_MAX;
        if(mode==3)mapping.file.inode=0;if(mode==4)mapping.offset=UINT64_MAX;if(mode==5)identity.fail_at=1;
        if(mode==6)identity.change_at=1;if(mode==7)resident.fail_at=1;if(mode==8)file.fail_at=1;
        if(mode==9)resident.bytes[24]=1;if(mode==10)resident.fail_at=2;
        if(mode==11){resident.change_at=2;resident.change_index=24;}if(mode==12)identity.fail_at=2;
        if(mode==13)identity.change_at=2;if(mode==14)mapping.file.size=31;
      }
      const auto result=bind_macho_slice(mapping,identity,file,resident,out);
      if(name=="binding")CHECK(result==SliceFailure::none&&valid_slice_binding(out)&&out.slice.offset==4096&&same_file(out.mapping.file,mapping.file));
      else CHECK(result!=SliceFailure::none&&!out.mapping.address&&same_slice(out.slice,{}));
    }
  }else if(name=="binding_values") {
    Source file(fat()),resident(thin());Identity identity(file.bytes.size());SliceBinding value{};CHECK(bind_macho_slice({0x1000,4096,4096,identity.value},identity,file,resident,value)==SliceFailure::none);
    for(unsigned mode=0;mode<10;++mode){auto b=value;
      if(mode==0)b.slice.offset++;if(mode==1)b.slice.size=UINT64_MAX;if(mode==2)b.slice.format=SliceFormat::unknown;
      if(mode==3)b.slice.format=SliceFormat::thin;if(mode==4)b.mapping.file.size=artifact_file_limit+1;
      if(mode==5)b.slice.header[0]=0;if(mode==6)b.mapping.address=0;if(mode==7)b.mapping.size=31;
      if(mode==8){b.slice.offset=27;b.mapping.offset=27;}if(mode==9){b.slice.format=SliceFormat::fat64;b.slice.offset=39;b.mapping.offset=39;}
      CHECK(!valid_slice_binding(b));
    }
    CHECK(same_slice(value.slice,value.slice)&&!same_slice(value.slice,{}));
  }else CHECK(false);
}
}
int main(int argc,char**argv){CHECK(argc==2);test(argv[1]);}
