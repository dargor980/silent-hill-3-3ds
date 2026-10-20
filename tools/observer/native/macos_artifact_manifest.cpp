#include "sh3_observer/macos_artifact_manifest.hpp"
#include <cstring>
#include <fcntl.h>
#include <limits>
#include <sys/stat.h>
#include <unistd.h>
#include <utility>

namespace sh3::observer {
bool MacOSSha256::allowed() noexcept {
  if (stopped_ || !inspect_continue(control_, InspectionStep::digest)) {
    stopped_ = true; active_ = false; context_ = {}; return false;
  }
  return true;
}
bool MacOSSha256::begin() noexcept {
  if (!allowed()) return false;
  context_ = {};
  active_ = CC_SHA256_Init(&context_) == 1;
  return allowed() && active_;
}
bool MacOSSha256::update(const void* bytes, std::size_t size) noexcept {
  if (!allowed() || !active_ || !bytes || size > digest_block_size) { active_ = false; return false; }
  active_ = CC_SHA256_Update(&context_, bytes, static_cast<CC_LONG>(size)) == 1;
  return allowed() && active_;
}
bool MacOSSha256::finish(Sha256& out) noexcept {
  out = {};
  if (!allowed() || !active_) return false;
  active_ = false;
  const bool ok = CC_SHA256_Final(out.data(), &context_) == 1;
  context_ = {};
  if (!allowed() || !ok) { out = {}; return false; }
  return true;
}
namespace {
class Fd final {
public:
  explicit Fd(int value = -1, bool* close_ok = nullptr) noexcept : value_(value), close_ok_(close_ok) {}
  ~Fd() { (void)close_verified(); }
  Fd(const Fd&) = delete;
  Fd& operator=(const Fd&) = delete;
  int get() const noexcept { return value_; }
  void reset(int value) noexcept { (void)close_verified(); value_ = value; }
  bool close_verified() noexcept {
    const auto value = release();
    const bool ok = value < 0 || ::close(value) == 0;
    if (!ok && close_ok_) *close_ok_ = false;
    return ok;
  }
  int release() noexcept { const int result = value_; value_ = -1; return result; }
private:
  int value_;
  bool* close_ok_;
};
int walk(int base, std::string_view name, bool directory, InspectionControl* control, bool* close_ok) noexcept {
  if (!inspect_continue(control, InspectionStep::file_open) || !valid_artifact_name(name)) return -1;
  Fd current(fcntl(base, F_DUPFD_CLOEXEC, 0), close_ok);
  if (current.get() < 0) return -1;
  std::size_t start = 0;
  while (start < name.size()) {
    if (!inspect_continue(control, InspectionStep::file_open)) return -1;
    const auto slash = name.find('/', start);
    const bool last = slash == std::string_view::npos;
    const auto part = name.substr(start, last ? name.size() - start : slash - start);
    char component[256]{};
    std::memcpy(component, part.data(), part.size());
    const int flags = O_RDONLY | O_CLOEXEC | O_NOFOLLOW | O_NONBLOCK | ((!last || directory) ? O_DIRECTORY : 0);
    current.reset(openat(current.get(), component, flags));
    if (current.get() < 0 || !inspect_continue(control, InspectionStep::file_open)) return -1;
    if (last) return current.release();
    start = slash + 1;
  }
  return -1;
}
int open_root(std::string_view name, InspectionControl* control, bool* close_ok) noexcept {
  if (!inspect_continue(control, InspectionStep::file_open) || name.size() < 2 || name.front() != '/') return -1;
  Fd slash(open("/", O_RDONLY | O_DIRECTORY | O_CLOEXEC), close_ok);
  if (slash.get() < 0) return -1;
  return walk(slash.get(), name.substr(1), true, control, close_ok);
}
bool file_object(int descriptor, FileObject& out) noexcept {
  out = {};
  struct stat s{};
  if (fstat(descriptor, &s) != 0 || !S_ISREG(s.st_mode) || s.st_size <= 0 ||
      s.st_mtimespec.tv_nsec < 0 || s.st_mtimespec.tv_nsec >= 1000000000 ||
      s.st_ctimespec.tv_nsec < 0 || s.st_ctimespec.tv_nsec >= 1000000000) return false;
  FileObject value{static_cast<std::uint32_t>(s.st_dev), s.st_ino, static_cast<std::uint64_t>(s.st_size),
    s.st_mtimespec.tv_sec, s.st_ctimespec.tv_sec, static_cast<std::uint32_t>(s.st_mtimespec.tv_nsec),
    static_cast<std::uint32_t>(s.st_ctimespec.tv_nsec)};
  if (!valid_file(value)) return false;
  out = value;
  return true;
}
bool same_directory(int a, int b) noexcept {
  struct stat x{}, y{};
  return fstat(a, &x) == 0 && fstat(b, &y) == 0 && S_ISDIR(x.st_mode) && S_ISDIR(y.st_mode) &&
    x.st_dev == y.st_dev && x.st_ino != 0 && x.st_ino == y.st_ino;
}
}
struct MacOSArtifactFiles::Impl {
  struct Item final : FileIdentitySource, ByteSource {
    Impl& owner;
    const std::string name;
    Fd fd;
    FileObject original{};
    MacOSSha256 hash;
    AnchoredDigest digest;
    bool valid{};
    Item(Impl& parent, std::string path) : owner(parent), name(std::move(path)),
      fd(walk(owner.root.get(), name, false, owner.control, &owner.close_ok), &owner.close_ok), hash(owner.control), digest(*this, *this, hash) {
      valid = owner.check(InspectionStep::file_identity) && fd.get() >= 0 && file_object(fd.get(), original) && owner.check(InspectionStep::file_identity);
    }
    bool read(FileObject& out) noexcept override {
      out = {};
      if (!valid || !owner.root_valid()) return false;
      Fd named(walk(owner.root.get(), name, false, owner.control, &owner.close_ok), &owner.close_ok);
      FileObject held{}, current{};
      if (!file_object(fd.get(), held) || !file_object(named.get(), current) ||
          !same_file(held, current) || !same_file(held, original) || !owner.check(InspectionStep::file_identity)) { valid = false; return false; }
      out = held;
      return true;
    }
    bool read_at(std::uint64_t offset, void* bytes, std::size_t wanted, std::size_t& got) noexcept override {
      got = 0;
      if (!owner.check(InspectionStep::file_read) || !valid || !owner.reader || offset > static_cast<std::uint64_t>(std::numeric_limits<off_t>::max())) return false;
      const auto n = owner.reader(fd.get(), bytes, wanted, static_cast<off_t>(offset));
      if (!owner.check(InspectionStep::file_read) || n < 0 || static_cast<std::uint64_t>(n) > wanted) return false;
      got = static_cast<std::size_t>(n);
      return true;
    }
  };
  bool failed{}, close_ok{true};
  InspectionControl* control;
  const std::string root_path;
  Fd root;
  ReadAt reader;
  std::vector<std::unique_ptr<Item>> items;
  Impl(std::string path, const std::vector<ExpectedFile>& expected, ReadAt read, InspectionControl* c)
    : control(c), root_path(std::move(path)), root(-1,&close_ok), reader(read) {
    if (!check(InspectionStep::preparation) || !valid_manifest(expected) || !reader) { failed = true; return; }
    root.reset(open_root(root_path, control, &close_ok));
    if (root.get() < 0) { failed = true; return; }
    for (const auto& file : expected) {
      if (!check(InspectionStep::preparation)) return;
      auto item = std::make_unique<Item>(*this, file.name);
      if (!item->valid) { failed = true; return; }
      items.push_back(std::move(item));
    }
  }
  bool check(InspectionStep step) noexcept {
    if (failed || !close_ok || !inspect_continue(control, step)) { failed = true; return false; }
    return true;
  }
  bool root_valid() noexcept {
    if (!check(InspectionStep::file_identity)) return false;
    Fd named(open_root(root_path, control, &close_ok), &close_ok);
    if (!same_directory(root.get(), named.get()) || !check(InspectionStep::file_identity)) { failed = true; return false; }
    return true;
  }
};
MacOSArtifactFiles::MacOSArtifactFiles(std::string root, const std::vector<ExpectedFile>& expected)
  : MacOSArtifactFiles(std::move(root), expected, ::pread, nullptr) {}
MacOSArtifactFiles::MacOSArtifactFiles(std::string root, const std::vector<ExpectedFile>& expected, ReadAt read)
  : MacOSArtifactFiles(std::move(root), expected, read, nullptr) {}
MacOSArtifactFiles::MacOSArtifactFiles(std::string root, const std::vector<ExpectedFile>& expected, InspectionControl& control)
  : MacOSArtifactFiles(std::move(root), expected, ::pread, &control) {}
MacOSArtifactFiles::MacOSArtifactFiles(std::string root, const std::vector<ExpectedFile>& expected, ReadAt read, InspectionControl* control)
  : impl_(std::make_unique<Impl>(std::move(root), expected, read, control)) {}
MacOSArtifactFiles::~MacOSArtifactFiles() { (void)close(); }
bool MacOSArtifactFiles::close() noexcept {
  impl_->failed = true;
  for (const auto& item : impl_->items) {
    item->valid = false;
    if (!item->fd.close_verified()) impl_->close_ok = false;
  }
  if (!impl_->root.close_verified()) impl_->close_ok = false;
  return impl_->close_ok;
}
bool MacOSArtifactFiles::read(std::string_view name, FileDigest& out) noexcept {
  out = {};
  if (!impl_->check(InspectionStep::file_identity)) return false;
  for (const auto& item : impl_->items) {
    if (item->name != name) continue;
    if (item->digest.sample(out) == ManifestFailure::none && impl_->check(InspectionStep::file_identity)) return true;
    out = {};
    impl_->failed = true;
    return false;
  }
  impl_->failed = true;
  return false;
}
} // namespace sh3::observer
