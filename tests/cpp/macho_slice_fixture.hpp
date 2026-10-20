#pragma once
#include "sh3_observer/macho_slice.hpp"
#include <algorithm>
#include <cstring>
#include <vector>
namespace slice_fixture {
using Bytes=std::vector<std::uint8_t>;
inline void le32(Bytes& b,std::size_t p,std::uint32_t v){for(unsigned i=0;i<4;++i)b[p+i]=static_cast<std::uint8_t>(v>>(8*i));}
inline void be32(Bytes& b,std::size_t p,std::uint32_t v){for(unsigned i=0;i<4;++i)b[p+3-i]=static_cast<std::uint8_t>(v>>(8*i));}
inline void be64(Bytes& b,std::size_t p,std::uint64_t v){for(unsigned i=0;i<8;++i)b[p+7-i]=static_cast<std::uint8_t>(v>>(8*i));}
inline Bytes thin(std::uint32_t cpu=0x1000007,std::uint32_t sub=3) {
  Bytes b(64);le32(b,0,0xfeedfacf);le32(b,4,cpu);le32(b,8,sub);le32(b,12,6);le32(b,16,1);le32(b,20,8);return b;
}
inline Bytes fat(bool wide=false,unsigned count=2) {
  Bytes b(4096*count+64);be32(b,0,wide?0xcafebabf:0xcafebabe);be32(b,4,count);
  for(unsigned i=0;i<count;++i){const auto cpu=i==1?0x100000cU:0x1000007U,sub=i==1?0x80000002U:i+3;
    const auto p=8+i*(wide?32:20);be32(b,p,cpu);be32(b,p+4,sub);
    if(wide){be64(b,p+8,4096*(i+1));be64(b,p+16,64);be32(b,p+24,12);}
    else{be32(b,p+8,4096*(i+1));be32(b,p+12,64);be32(b,p+16,12);}
    const auto header=thin(cpu,sub);std::copy(header.begin(),header.end(),b.begin()+4096*(i+1));
  }return b;
}
struct Source final:sh3::observer::ByteSource {
  Bytes bytes;int calls{},fail_at{},short_at{},change_at{},change_index{};std::size_t requested{};
  explicit Source(Bytes data):bytes(std::move(data)){}
  bool read_at(std::uint64_t offset,void* out,std::size_t size,std::size_t& got)noexcept override {
    ++calls;got=0;requested+=size;
    if(calls==change_at)++bytes[change_index];
    if(calls==fail_at||offset>bytes.size()||size>bytes.size()-offset)return false;
    got=size-(calls==short_at?1:0);std::memcpy(out,bytes.data()+offset,got);return true;
  }
};
inline sh3::observer::FileObject object(std::size_t size){return {1,2,size,3,4,5,6};}
struct Identity final:sh3::observer::FileIdentitySource {
  sh3::observer::FileObject value;int calls{},fail_at{},change_at{};
  explicit Identity(std::size_t size):value(object(size)){}
  bool read(sh3::observer::FileObject& out)noexcept override{++calls;out=value;if(calls==change_at)++out.inode;return calls!=fail_at;}
};
}
