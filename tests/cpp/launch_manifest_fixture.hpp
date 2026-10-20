#pragma once
#include "sh3_observer/launch_manifest.hpp"
#include <algorithm>
#include <cstring>
namespace launch_fixture {
using namespace sh3::observer;
using Bytes=std::vector<std::uint8_t>;
inline Sha256 tag(unsigned n){Sha256 s{};s[0]=n;return s;}
inline LaunchManifest manifest(){LaunchManifest m;m.roots={"/a","/b"};m.files={{0,{"x",64,tag(1)}},{1,{"y",128,tag(2)}}};m.cache[0]=1;m.policy_evidence=tag(2);m.platform_evidence=tag(3);return m;}
inline void number(Bytes& b,std::uint64_t n,unsigned width){for(unsigned i=0;i<width;++i)b.push_back(static_cast<std::uint8_t>(n>>(8*i)));}
inline void word(Bytes& b,std::size_t at,std::uint32_t n){for(unsigned i=0;i<4;++i)b[at+i]=static_cast<std::uint8_t>(n>>(8*i));}
inline Bytes encode(const LaunchManifest& m){
  Bytes b={'S','H','3','L','M','0','0','1'};number(b,m.roots.size(),4);number(b,m.files.size(),4);number(b,m.main_file,4);
  b.insert(b.end(),m.cache.begin(),m.cache.end());b.insert(b.end(),m.policy_evidence.begin(),m.policy_evidence.end());b.insert(b.end(),m.platform_evidence.begin(),m.platform_evidence.end());
  for(const auto& root:m.roots){number(b,root.size(),4);b.insert(b.end(),root.begin(),root.end());}
  for(const auto& f:m.files){number(b,f.root,4);number(b,f.file.name.size(),4);number(b,f.file.size,8);b.insert(b.end(),f.file.sha256.begin(),f.file.sha256.end());b.insert(b.end(),f.file.name.begin(),f.file.name.end());}return b;
}
struct Source final:ByteSource,FileIdentitySource {
  Bytes data;int reads{},identities{},fail_at{},short_at{},change_at{};bool extra{};std::uint64_t declared{};
  explicit Source(Bytes b):data(std::move(b)),declared(data.size()){}
  bool read(FileObject& out)noexcept override{++identities;out={1,2,declared,3,4,5,6};if(identities==change_at)++out.inode;return true;}
  bool read_at(std::uint64_t at,void* dst,std::size_t want,std::size_t& got)noexcept override{
    ++reads;got=0;if(reads==fail_at)return false;
    if(at==data.size()){got=extra?1:0;return true;}
    if(at>data.size()||want>data.size()-at)return false;
    got=want-(reads==short_at?1:0);std::memcpy(dst,data.data()+at,got);return true;
  }
};
struct Hash final:DigestEngine {
  int fail{};unsigned calls{};std::uint64_t sum{};
  bool begin()noexcept override{sum=0;calls=0;return fail!=1;}
  bool update(const void* p,std::size_t n)noexcept override{++calls;auto b=static_cast<const std::uint8_t*>(p);for(std::size_t i=0;i<n;++i)sum=sum*33+b[i];return fail!=2;}
  bool finish(Sha256& out)noexcept override{out={};for(unsigned i=0;i<8;++i)out[i]=static_cast<std::uint8_t>(sum>>(8*i));return fail!=3;}
};
inline Sha256 digest(const Bytes& b){Hash h;Sha256 s{};h.begin();h.update(b.data(),b.size());h.finish(s);return s;}
}
