#pragma once
#include <vector>
#include <cstdint>
#include <cstring>
namespace layout_fixture {
using Bytes=std::vector<unsigned char>;
inline void put32(Bytes& b,std::size_t p,std::uint32_t v){for(unsigned i=0;i<4;++i)b[p+i]=static_cast<unsigned char>(v>>(8*i));}
inline void put64(Bytes& b,std::size_t p,std::uint64_t v){for(unsigned i=0;i<8;++i)b[p+i]=static_cast<unsigned char>(v>>(8*i));}
inline void segment(Bytes& b,const char* name,std::uint64_t address,std::uint64_t size,std::uint64_t off,std::uint64_t file,std::uint32_t prot,unsigned sections=0,unsigned flags=0){
  auto start=b.size();b.resize(start+72+80*sections);put32(b,start,0x19);put32(b,start+4,72+80*sections);
  std::memcpy(b.data()+start+8,name,std::strlen(name));put64(b,start+24,address);put64(b,start+32,size);put64(b,start+40,off);put64(b,start+48,file);
  put32(b,start+56,prot);put32(b,start+60,prot);put32(b,start+64,sections);put32(b,start+68,flags);
}
inline Bytes valid(){
  Bytes b(32);put32(b,0,0xfeedfacf);put32(b,4,0x01000007);put32(b,8,3);put32(b,12,2);put32(b,16,4);put32(b,24,0x80000000);
  segment(b,"__PAGEZERO",0,0x100000000,0,0,0);
  segment(b,"__TEXT",0x100000000,16384,0,16384,5,1,4);
  segment(b,"__DATA",0x100004000,16384,16384,4096,3);
  auto p=b.size();b.resize(p+8);put32(b,p,0x9876);put32(b,p+4,8);
  put32(b,20,static_cast<std::uint32_t>(b.size()-32));return b;
}
}
