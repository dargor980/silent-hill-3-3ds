#include "sh3_observer/launch_manifest.hpp"
#include <algorithm>
#include <cstring>
#include <utility>

namespace sh3::observer {
namespace {
template<std::size_t N> bool nonzero(const std::array<std::uint8_t,N>& a) noexcept {
  return std::any_of(a.begin(),a.end(),[](auto n){ return n != 0; });
}
std::string key(const LaunchFile& f) { return std::to_string(f.root)+"/"+f.file.name; }
class Cursor {
public:
  Cursor(const std::uint8_t* p,std::size_t n) : p_(p), left_(n) {}
  bool bytes(void* out,std::size_t n) {
    if (n > left_) return false;
    std::memcpy(out,p_,n);p_+=n;left_-=n;return true;
  }
  bool number(std::uint64_t& out,unsigned width) {
    if (width > left_) return false;
    out=0;for(unsigned i=0;i<width;++i)out|=std::uint64_t(p_[i])<<(8*i);
    p_+=width;left_-=width;return true;
  }
  bool text(std::string& out,std::size_t minimum,std::size_t maximum) {
    std::uint64_t n{};
    if (!number(n,4) || n < minimum || n > maximum || n > left_) return false;
    out.assign(reinterpret_cast<const char*>(p_),n);p_+=n;left_-=n;return true;
  }
  bool empty() const { return !left_; }
private:
  const std::uint8_t* p_;std::size_t left_;
};
}
bool valid_launch_manifest(const LaunchManifest& m) noexcept {
  if (m.roots.empty() || m.roots.size() > launch_root_capacity || m.files.empty() ||
      m.files.size() > artifact_file_capacity || m.main_file >= m.files.size() ||
      !nonzero(m.cache) || !nonzero(m.policy_evidence) || !nonzero(m.platform_evidence)) return false;
  for(std::size_t i=0;i<m.roots.size();++i) {
    const auto& root=m.roots[i];
    if (root.size()<2 || root[0]!='/' || !valid_artifact_name(std::string_view(root).substr(1))) return false;
    for(std::size_t j=0;j<i;++j)if(root==m.roots[j])return false;
  }
  std::array<bool,launch_root_capacity> used{};
  std::uint64_t total{};const LaunchFile* previous=nullptr;
  for(const auto& f:m.files) {
    if(f.root>=m.roots.size() || f.file.name.size()>1022 || !valid_artifact_name(f.file.name) ||
       !f.file.size || f.file.size>artifact_file_limit || f.file.size>artifact_total_limit-total || !nonzero(f.file.sha256))return false;
    if(previous && (f.root<previous->root || (f.root==previous->root && f.file.name<=previous->file.name)))return false;
    total+=f.file.size;used[f.root]=true;previous=&f;
  }
  return std::all_of(used.begin(),used.begin()+m.roots.size(),[](bool v){return v;});
}
std::vector<ExpectedFile> launch_expected_files(const LaunchManifest& m) {
  if(!valid_launch_manifest(m))return {};
  std::vector<ExpectedFile> out;out.reserve(m.files.size());
  for(const auto& f:m.files)out.push_back({key(f),f.file.size,f.file.sha256});
  return out;
}
LaunchFailure decode_launch_manifest(const std::uint8_t* data,std::size_t size,LaunchManifest& out) {
  out={};
  if(!data || size<100 || size>launch_manifest_limit)return LaunchFailure::invalid;
  Cursor c(data,size);std::array<char,8> magic{};std::uint64_t roots{},files{},main{};LaunchManifest m;
  if(!c.bytes(magic.data(),magic.size()) || magic!=std::array<char,8>{'S','H','3','L','M','0','0','1'} ||
     !c.number(roots,4) || !roots || roots>launch_root_capacity || !c.number(files,4) || !files || files>artifact_file_capacity ||
     !c.number(main,4) || main>=files || !c.bytes(m.cache.data(),m.cache.size()) ||
     !c.bytes(m.policy_evidence.data(),32) || !c.bytes(m.platform_evidence.data(),32))return LaunchFailure::malformed;
  m.main_file=main;m.roots.resize(roots);m.files.resize(files);
  for(auto& root:m.roots)if(!c.text(root,2,1025))return LaunchFailure::malformed;
  for(auto& f:m.files) {
    std::uint64_t root{},length{};
    if(!c.number(root,4) || root>=roots || !c.number(length,4) || !length || length>1022 ||
       !c.number(f.file.size,8) || !c.bytes(f.file.sha256.data(),32))return LaunchFailure::malformed;
    f.root=root;f.file.name.resize(length);
    if(!c.bytes(f.file.name.data(),length))return LaunchFailure::malformed;
  }
  if(!c.empty() || !valid_launch_manifest(m))return LaunchFailure::malformed;
  out=std::move(m);return LaunchFailure::none;
}
LaunchFailure read_launch_manifest(FileIdentitySource& identity,ByteSource& bytes,DigestEngine& hash,
    const Sha256& expected,LaunchManifest& out) {
  out={};if(!nonzero(expected))return LaunchFailure::invalid;
  FileObject before{},after{};
  if(!identity.read(before) || !valid_file(before))return LaunchFailure::identity;
  if(before.size<100 || before.size>launch_manifest_limit)return LaunchFailure::invalid;
  std::vector<std::uint8_t> data(before.size);
  if(!hash.begin())return LaunchFailure::unavailable;
  for(std::size_t offset=0;offset<data.size();) {
    const auto wanted=std::min(digest_block_size,data.size()-offset);std::size_t got{};
    if(!bytes.read_at(offset,data.data()+offset,wanted,got) || got!=wanted || !hash.update(data.data()+offset,wanted))return LaunchFailure::unavailable;
    offset+=wanted;
  }
  std::uint8_t trailing{};std::size_t got{};Sha256 digest{};
  if(!bytes.read_at(data.size(),&trailing,1,got) || got || !hash.finish(digest))return LaunchFailure::unavailable;
  if(!identity.read(after) || !same_file(before,after))return LaunchFailure::identity;
  if(digest!=expected)return LaunchFailure::digest;
  return decode_launch_manifest(data.data(),data.size(),out);
}
} // namespace sh3::observer
