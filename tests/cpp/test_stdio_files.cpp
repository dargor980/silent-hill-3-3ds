#include "check.hpp"
#include "sh3/application/options_store.hpp"
#include "sh3/platform/stdio_files.hpp"
#include <algorithm>
#include <cerrno>
#include <cstdlib>
#include <filesystem>
#include <string>
#include <unistd.h>

namespace {
using E = sh3::ports::FileError;
using Id = sh3::ports::FileId;
using sh3::platform::StdioFiles;
enum class Fault { none, open, read, short_write, write_error, flush, close };
Fault fault = Fault::none;
int error_code = 0;
unsigned opened = 0, closed = 0;
std::FILE *open_file(const char *path, const char *mode) {
    if (fault == Fault::open) {
        errno = error_code;
        return nullptr;
    }
    auto *file = std::fopen(path, mode);
    if (file) {
        ++opened;
    }
    return file;
}
std::size_t read_file(void *buffer, std::size_t size, std::size_t count, std::FILE *file) {
    const auto read = std::fread(buffer, size, fault == Fault::read ? 4 : count, file);
    if (fault == Fault::read) {
        errno = error_code;
    }
    return read;
}
std::size_t write_file(const void *buffer, std::size_t size, std::size_t count, std::FILE *file) {
    const auto written = std::fwrite(buffer, size, fault == Fault::short_write ? 4 : count, file);
    if (fault == Fault::short_write || fault == Fault::write_error) {
        errno = error_code;
    }
    return written;
}
int file_error(std::FILE *file) noexcept {
    return fault == Fault::read || fault == Fault::write_error ? 1 : std::ferror(file);
}
int flush_file(std::FILE *file) {
    if (fault == Fault::flush) {
        errno = error_code;
        return EOF;
    }
    return std::fflush(file);
}
int close_file(std::FILE *file) {
    ++closed;
    const auto result = std::fclose(file);
    if (fault == Fault::close) {
        errno = error_code;
        return EOF;
    }
    return result;
}
const sh3::platform::StdioApi api{open_file,  read_file,  write_file,
                                  file_error, flush_file, close_file};
struct Directory {
    std::string root;
    Directory() {
        auto path = (std::filesystem::temp_directory_path() / "sh3-files-XXXXXX").string();
        CHECK(mkdtemp(path.data()) != nullptr);
        root = path;
    }
    ~Directory() { std::filesystem::remove_all(root); }
};
void raw(const std::string &path, std::size_t size) {
    auto *file = std::fopen(path.c_str(), "wb");
    CHECK(file);
    for (std::size_t i = 0; i < size; ++i) {
        CHECK(std::fputc('x', file) != EOF);
    }
    CHECK(std::fclose(file) == 0);
}
} // namespace

int main() {
    Directory dir;
    StdioFiles files(dir.root.c_str(), api);
    const auto bytes = sh3::domain::encode_options({{false}, 1});
    CHECK(files.read(Id::probe).error == E::missing);
    CHECK(files.write(Id::probe, bytes.data(), bytes.size()) == E::invalid_target);
    for (std::size_t size : {0U, 8U, 16U, 32U, 33U, 1024U}) {
        raw(dir.root + "/probe.txt", size);
        auto read = files.read(Id::probe);
        CHECK(read.error == (size > 32 ? E::too_large : E::ok));
        if (size <= 32) {
            CHECK(read.size == size);
        }
    }
    CHECK(files.write(Id::options_a, bytes.data(), bytes.size()) == E::ok);
    auto read = files.read(Id::options_a);
    CHECK(read.error == E::ok && read.size == 16);
    CHECK(std::equal(bytes.begin(), bytes.end(), read.bytes.begin()));
    const std::string long_root(192, 'x');
    for (const char *root : std::array<const char *, 3>{nullptr, "", long_root.c_str()}) {
        StdioFiles invalid(root);
        CHECK(invalid.read(Id::probe).error == E::invalid_path);
        CHECK(invalid.write(Id::options_a, bytes.data(), 16) == E::invalid_path);
    }
    CHECK(files.read(static_cast<Id>(99)).error == E::invalid_path);
    CHECK(files.write(static_cast<Id>(99), bytes.data(), 16) == E::invalid_path);
    CHECK(files.write(Id::options_a, nullptr, 16) == E::invalid_target);
    CHECK(files.write(Id::options_a, bytes.data(), 0) == E::invalid_target);
    CHECK(files.write(Id::options_a, bytes.data(), 33) == E::invalid_target);

    fault = Fault::open;
    for (int code : {ENOENT, EACCES, EPERM, EROFS, ENOSPC, EIO, 0}) {
        error_code = code;
        const auto expected = code == ENOENT   ? E::missing
                              : code == ENOSPC ? E::no_space
                              : (code == EACCES || code == EPERM || code == EROFS)
                                  ? E::permission_denied
                                  : E::read_failed;
        CHECK(files.read(Id::options_a).error == expected);
        CHECK(files.write(Id::options_b, bytes.data(), 16) ==
              (expected == E::read_failed ? E::write_failed : expected));
    }
    fault = Fault::read;
    error_code = EIO;
    CHECK(files.read(Id::options_a).error == E::read_failed);
    for (auto f : {Fault::short_write, Fault::write_error, Fault::flush, Fault::close}) {
        fault = f;
        for (int code : {EIO, ENOSPC}) {
            error_code = code;
            const auto expected = code == ENOSPC      ? E::no_space
                                  : f == Fault::flush ? E::flush_failed
                                  : f == Fault::close ? E::close_failed
                                                      : E::write_failed;
            CHECK(files.write(Id::options_b, bytes.data(), 16) == expected);
            CHECK(opened == closed);
        }
    }
    fault = Fault::close;
    error_code = EIO;
    CHECK(files.read(Id::options_a).error == E::close_failed);
    fault = Fault::none;

    // Real filesystem adapter + application: restore, reopen, and failed candidate.
    std::filesystem::remove(dir.root + "/options-b.dat");
    sh3::application::OptionsStore store(files, files);
    CHECK(store.load() == E::ok && !store.current().tone_enabled);
    CHECK(store.save({}) == E::ok && store.generation() == 2);
    sh3::application::OptionsStore reopened(files, files);
    CHECK(reopened.load() == E::ok && reopened.current().tone_enabled);
    const auto previous = files.read(Id::options_b).bytes;
    fault = Fault::short_write;
    error_code = ENOSPC;
    CHECK(reopened.save({false}) == E::no_space && reopened.current().tone_enabled);
    fault = Fault::none;
    CHECK(files.read(Id::options_b).bytes == previous);
    CHECK(reopened.load() == E::invalid_data && reopened.generation() == 2);
    CHECK(opened == closed);
    for (unsigned i = 0; i <= static_cast<unsigned>(E::generation_exhausted); ++i) {
        CHECK(std::string(sh3::platform::file_error_name(static_cast<E>(i))) != "UNKNOWN");
    }
    CHECK(std::string(sh3::platform::file_error_name(static_cast<E>(999))) == "UNKNOWN");
}
