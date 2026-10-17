#include "sh3/platform/stdio_files.hpp"
#include <algorithm>
#include <cerrno>
#include <cstring>

namespace sh3::platform {
namespace {
using E = ports::FileError;
E io_error(int code, E fallback) noexcept {
    switch (code) {
    case ENOENT:
        return E::missing;
    case EACCES:
    case EPERM:
    case EROFS:
        return E::permission_denied;
    case ENOSPC:
        return E::no_space;
    default:
        return fallback;
    }
}
class File final {
  public:
    File(std::FILE *file, StdioApi api) noexcept : file_(file), api_(api) {}
    ~File() {
        if (file_ != nullptr) {
            api_.close(file_);
        }
    }
    File(const File &) = delete;
    File &operator=(const File &) = delete;
    int close() noexcept {
        auto *file = file_;
        file_ = nullptr;
        return api_.close(file);
    }

  private:
    std::FILE *file_;
    StdioApi api_;
};
} // namespace

StdioFiles::StdioFiles(const char *root, StdioApi api) noexcept : api_(api) {
    if (root != nullptr && *root != '\0' && std::strlen(root) < root_.size()) {
        std::strcpy(root_.data(), root);
        valid_ = true;
    }
}
bool StdioFiles::path(ports::FileId file, std::array<char, 256> &output) const noexcept {
    if (!valid_) {
        return false;
    }
    const char *name = nullptr;
    switch (file) {
    case ports::FileId::probe:
        name = "probe.txt";
        break;
    case ports::FileId::options_a:
        name = "options-a.dat";
        break;
    case ports::FileId::options_b:
        name = "options-b.dat";
        break;
    default:
        return false;
    }
    std::snprintf(output.data(), output.size(), "%s/%s", root_.data(), name);
    return true; // root length is bounded to 191 and each fixed filename to 13.
}
ports::FileRead StdioFiles::read(ports::FileId id) noexcept {
    ports::FileRead result;
    std::array<char, 256> name{};
    if (!path(id, name)) {
        result.error = E::invalid_path;
        return result;
    }
    errno = 0;
    auto *handle = api_.open(name.data(), "rb");
    if (handle == nullptr) {
        result.error = io_error(errno, E::read_failed);
        return result;
    }
    File file(handle, api_);
    std::array<std::uint8_t, 33> buffer{};
    errno = 0;
    const auto size = api_.read(buffer.data(), 1, buffer.size(), handle);
    const int read_errno = errno;
    if (api_.error(handle) != 0) {
        result.error = io_error(read_errno, E::read_failed);
    } else if (size > result.bytes.size()) {
        result.error = E::too_large;
    } else {
        result.size = size;
        std::copy_n(buffer.begin(), size, result.bytes.begin());
    }
    errno = 0;
    if (file.close() != 0 && result.error == E::ok) {
        result.error = io_error(errno, E::close_failed);
    }
    return result;
}
ports::FileError StdioFiles::write(ports::FileId id, const std::uint8_t *bytes,
                                   std::size_t size) noexcept {
    if (id == ports::FileId::probe || bytes == nullptr || size == 0 || size > 32) {
        return E::invalid_target;
    }
    std::array<char, 256> name{};
    if (!path(id, name)) {
        return E::invalid_path;
    }
    errno = 0;
    auto *handle = api_.open(name.data(), "wb");
    if (handle == nullptr) {
        return io_error(errno, E::write_failed);
    }
    File file(handle, api_);
    E error = E::ok;
    errno = 0;
    const auto written = api_.write(bytes, 1, size, handle);
    const int write_errno = errno;
    if (written != size || api_.error(handle) != 0) {
        error = io_error(write_errno, E::write_failed);
    } else {
        errno = 0;
        if (api_.flush(handle) != 0) {
            error = io_error(errno, E::flush_failed);
        }
    }
    errno = 0;
    if (file.close() != 0 && error == E::ok) {
        error = io_error(errno, E::close_failed);
    }
    return error;
}
const char *file_error_name(ports::FileError error) noexcept {
    switch (error) {
    case E::ok:
        return "OK";
    case E::missing:
        return "MISSING";
    case E::permission_denied:
        return "PERMISSION_DENIED";
    case E::no_space:
        return "NO_SPACE";
    case E::invalid_path:
        return "INVALID_PATH";
    case E::invalid_target:
        return "INVALID_TARGET";
    case E::read_failed:
        return "READ_FAILED";
    case E::too_large:
        return "TOO_LARGE";
    case E::write_failed:
        return "WRITE_FAILED";
    case E::flush_failed:
        return "FLUSH_FAILED";
    case E::close_failed:
        return "CLOSE_FAILED";
    case E::invalid_data:
        return "INVALID_DATA";
    case E::verify_failed:
        return "VERIFY_FAILED";
    case E::ambiguous:
        return "AMBIGUOUS";
    case E::generation_exhausted:
        return "GENERATION_EXHAUSTED";
    }
    return "UNKNOWN";
}
} // namespace sh3::platform
