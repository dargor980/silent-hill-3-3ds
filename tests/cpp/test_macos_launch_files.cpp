#include "sh3_observer/macos_launch_files.hpp"
#include "sh3_observer/macos_artifact_manifest.hpp"
#include "sh3_observer/macos_page_binding.hpp"
#include "launch_manifest_fixture.hpp"
#include "check.hpp"
#include <filesystem>
#include <fstream>
#include <sys/wait.h>
#include <unistd.h>
using namespace sh3::observer;
namespace fs=std::filesystem;
namespace {
void write(const fs::path& p,const std::string& s){std::ofstream out(p,std::ios::binary);out<<s;CHECK(out.good());}
Sha256 digest(const std::string& s){MacOSSha256 h;Sha256 out{};CHECK(h.begin()&&h.update(s.data(),s.size())&&h.finish(out));return out;}
void test(const std::string& n,const fs::path& root){
  fs::create_directories(root);std::string pattern=(root/"case-XXXXXX").string();CHECK(mkdtemp(pattern.data()));fs::path dir(pattern);
  fs::create_directory(dir/"a");fs::create_directory(dir/"b");write(dir/"a/x","alpha");write(dir/"b/y","bravo");
  auto m=launch_fixture::manifest();m.roots={(dir/"a").string(),(dir/"b").string()};m.files[0].file={"x",5,digest("alpha")};m.files[1].file={"y",5,digest("bravo")};
  if(n=="config_hash"){
    const auto bytes=launch_fixture::encode(launch_fixture::manifest());const auto p=dir/"manifest";
    write(p,std::string(bytes.begin(),bytes.end()));MacOSPageAnchor anchor(p.string());MacOSSha256 hash;LaunchManifest decoded;
    const std::string fixed="23df0fd85f52663166910701c3fbcd5f7dd74fd219adea67391325e274550c69";Sha256 expected{};
    for(unsigned i=0;i<32;++i)expected[i]=static_cast<std::uint8_t>(std::stoul(fixed.substr(i*2,2),nullptr,16));
    CHECK(read_launch_manifest(anchor,anchor,hash,expected,decoded)==LaunchFailure::none&&decoded.roots[0]=="/a");
    expected[0]^=1;CHECK(read_launch_manifest(anchor,anchor,hash,expected,decoded)==LaunchFailure::digest&&decoded.files.empty());return;
  }
  if(n=="invalid"){m.cache={};MacOSLaunchFiles files(m);FileDigest d{};CHECK(!files.read("0/x",d)&&!d.object.inode);return;}
  if(n=="symlink"){
    fs::rename(dir/"a/x",dir/"a/real");fs::create_symlink(dir/"a/real",dir/"a/x");MacOSLaunchFiles files(m);FileDigest d{};CHECK(!files.read("0/x",d)&&!d.object.inode);return;
  }
  MacOSLaunchFiles files(m);ManifestGuard guard(launch_expected_files(m),files);auto result=guard.sample();CHECK(result.failure==ManifestFailure::none&&result.count==2);
  FileDigest d{};
  if(n=="stable"){
    m.roots[0]="/changed";m.files.clear();CHECK(guard.sample().failure==ManifestFailure::none);CHECK(files.read("0/x",d)&&d.sha256==digest("alpha"));return;
  }else if(n=="fork"){
    auto child=fork();CHECK(child>=0);if(!child)_exit(!files.read("0/x",d)&&!d.object.inode?0:1);
    int status{};CHECK(waitpid(child,&status,0)==child&&WIFEXITED(status)&&WEXITSTATUS(status)==0);CHECK(guard.sample().failure==ManifestFailure::none);return;
  }else if(n=="unknown"){
    CHECK(!files.read("0/../x",d)&&!d.object.inode);CHECK(!files.read("0/x",d));return;
  }else if(n=="substitution"){
    write(dir/"replacement","alpha");fs::rename(dir/"replacement",dir/"a/x");
  }else if(n=="unlink"){fs::rename(dir/"a/x",dir/"removed");
  }else if(n=="root_replace"){
    fs::rename(dir/"a",dir/"old");fs::create_directory(dir/"a");write(dir/"a/x","alpha");
  }else if(n=="modify"){write(dir/"a/x","alphx");
  }else CHECK(false);
  CHECK(guard.sample().failure==ManifestFailure::unavailable);CHECK(!files.read("1/y",d)&&!d.object.inode);
}
}
int main(int argc,char** argv){CHECK(argc==3);test(argv[1],argv[2]);}
