#include "sh3_observer/macos_artifact_manifest.hpp"
#include "check.hpp"
#include <filesystem>
#include <fstream>
#include <sstream>
#include <unistd.h>
using namespace sh3::observer;
namespace fs=std::filesystem;
namespace {
Sha256 hex(const std::string& s) {
  CHECK(s.size()==64);Sha256 out{};
  for(std::size_t i=0;i<32;++i)out[i]=static_cast<std::uint8_t>(std::stoul(s.substr(2*i,2),nullptr,16));
  return out;
}
const Sha256 abc=hex("ba7816bf8f01cfea414140de5dae2223b00361a396177a9cb410ff61f20015ad");
const Sha256 million=hex("cdc76e5c9914fb9281a1c7e284d73e67f1809a48a497200e046d39ccc7112cd0");
void write(const fs::path& p,const std::string& bytes) {std::ofstream s(p,std::ios::binary);s<<bytes;CHECK(s.good());}
fs::path directory(const fs::path& base) {
  fs::create_directories(base);auto pattern=(base/"case-XXXXXX").string();CHECK(mkdtemp(pattern.data()));return pattern;
}
std::vector<ExpectedFile> config() {return {{"a",3,abc},{"sub/b",1000000,million}};}
void create(const fs::path& p) {fs::create_directories(p/"sub");write(p/"a","abc");write(p/"sub/b",std::string(1000000,'a'));}
int fault=0;fs::path changing;
ssize_t faulty_read(int fd,void* out,std::size_t size,off_t offset) {
  if(fault==1)return -1;
  if(fault==2)return 0;
  if(fault==3)return static_cast<ssize_t>(size+1);
  const auto result=pread(fd,out,size,offset);
  if(fault==4){fault=0;write(changing,"new");}
  return result;
}
void hash_vectors() {
  MacOSSha256 hash;Sha256 out{};CHECK(!hash.finish(out));CHECK(!hash.update("x",1));
  CHECK(hash.begin());CHECK(hash.finish(out));CHECK(out==hex("e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"));
  CHECK(hash.begin());CHECK(hash.update("abc",3));CHECK(hash.finish(out));CHECK(out==abc);
  CHECK(hash.begin());CHECK(!hash.update(nullptr,1));CHECK(!hash.finish(out));CHECK(out==Sha256{});
  CHECK(hash.begin());CHECK(!hash.update("x",digest_block_size+1));CHECK(!hash.finish(out));
}
void native(const std::string& scenario,const fs::path& base) {
  auto dir=directory(base);create(dir);auto expected=config();
  if(scenario=="bad_digest")++expected[0].sha256[0];
  if(scenario=="missing")fs::rename(dir/"a",dir/"missing");
  if(scenario=="file_symlink"){fs::rename(dir/"a",dir/"original");fs::create_symlink("original",dir/"a");}
  if(scenario=="dir_symlink"){fs::rename(dir/"sub",dir/"actual");fs::create_directory_symlink("actual",dir/"sub");}
  if(scenario=="not_file"){fs::rename(dir/"a",dir/"original");fs::create_directory(dir/"a");}
  if(scenario=="empty")write(dir/"a","");
  if(scenario=="read_error")fault=1;
  if(scenario=="read_short")fault=2;
  if(scenario=="read_long")fault=3;
  if(scenario=="during_read"){fault=4;changing=dir/"a";}
  MacOSArtifactFiles files(dir.string(),expected,faulty_read);ManifestGuard guard(expected,files);
  if(scenario=="bad_digest"){CHECK(guard.sample().failure==ManifestFailure::mismatch);return;}
  if(scenario=="missing"||scenario=="file_symlink"||scenario=="dir_symlink"||scenario=="not_file"||scenario=="empty"||scenario=="read_error"||scenario=="read_short"||scenario=="read_long"||scenario=="during_read") {
    CHECK(guard.sample().failure==ManifestFailure::unavailable);fault=0;
    if(scenario!="not_file")write(dir/"a","abc");
    CHECK(guard.sample().failure==ManifestFailure::unavailable);return;
  }
  auto before=guard.sample();CHECK(before.failure==ManifestFailure::none);CHECK(before.count==2);
  if(scenario=="stable") {
    CHECK(guard.sample().failure==ManifestFailure::none);
    FileDigest value{};CHECK(!files.read("unlisted",value));CHECK(value.object.inode==0);CHECK(!files.read("a",value));return;
  }
  if(scenario=="replace_same"||scenario=="replace_different") {
    write(dir/"new",scenario=="replace_same"?"abc":"xyz");fs::rename(dir/"new",dir/"a");
  } else if(scenario=="replace_root") {
    fs::rename(dir,dir.string()+"-old");create(dir);
  } else if(scenario=="replace_dir_symlink") {
    fs::rename(dir/"sub",dir/"actual");fs::create_directory_symlink("actual",dir/"sub");
  } else if(scenario=="modify")write(dir/"a","abd");
  else CHECK(false);
  CHECK(guard.sample().failure==ManifestFailure::unavailable);CHECK(guard.sample().count==0);
}
void roots(const fs::path& base) {
  auto dir=directory(base);create(dir);FileDigest out{};
  fs::create_directory_symlink(dir,dir.string()+"-link");
  for(const auto& name: {std::string{},std::string("relative"),std::string("/"),dir.string()+"/../missing",dir.string()+"-link",(dir/"a").string()}) {
    MacOSArtifactFiles bad(name,config());CHECK(!bad.read("a",out));CHECK(out.object.inode==0);
  }
  MacOSArtifactFiles null_read(dir.string(),config(),nullptr);CHECK(!null_read.read("a",out));
  MacOSArtifactFiles invalid(dir.string(),{});CHECK(!invalid.read("a",out));
}
void candidate(const fs::path& root,const fs::path& manifest) {
  std::ifstream stream(manifest);CHECK(stream.good());std::vector<ExpectedFile> entries;
  std::string line;
  while(std::getline(stream,line)) {
    std::istringstream in(line);std::string digest,name;std::uint64_t size{};CHECK(in>>digest>>size);
    CHECK(std::getline(in,name));CHECK(!name.empty()&&name.front()==' ');name.erase(0,1);entries.push_back({name,size,hex(digest)});
  }
  CHECK(entries.size()==42);CHECK(valid_manifest(entries));
  MacOSArtifactFiles files(root.string(),entries);ManifestGuard guard(entries,files);
  CHECK(guard.sample().failure==ManifestFailure::none);CHECK(guard.sample().failure==ManifestFailure::none);
  std::printf("candidate_manifest_files=%zu passes=4\n",entries.size());
}
}
int main(int argc,char** argv) {
  CHECK(argc>=3);const std::string mode=argv[1];
  if(mode=="vectors")hash_vectors();else if(mode=="roots")roots(argv[2]);
  else if(mode=="candidate"){CHECK(argc==4);candidate(argv[2],argv[3]);}
  else native(mode,argv[2]);
}
