#pragma once

#include "sh3/ports/files.hpp"
#include <cstdio>

namespace sh3::platform {
// Narrow stdio seam for deterministic short-I/O/flush/close failure tests.
// Production uses the C library on both host and 3DS.
struct StdioApi {
    decltype(&std::fopen) open;
    decltype(&std::fread) read;
    decltype(&std::fwrite) write;
    decltype(&std::ferror) error;
    decltype(&std::fflush) flush;
    decltype(&std::fclose) close;
};
inline const StdioApi system_stdio{std::fopen,  std::fread,  std::fwrite,
                                   std::ferror, std::fflush, std::fclose};

class StdioFiles final : public ports::IFileReader, public ports::IFileWriter {
  public:
    explicit StdioFiles(const char *root, StdioApi api = system_stdio) noexcept;
    [[nodiscard]] ports::FileRead read(ports::FileId file) noexcept override;
    [[nodiscard]] ports::FileError write(ports::FileId file, const std::uint8_t *bytes,
                                         std::size_t size) noexcept override;

  private:
    [[nodiscard]] bool path(ports::FileId file, std::array<char, 256> &output) const noexcept;
    std::array<char, 192> root_{};
    StdioApi api_;
    bool valid_{false};
};
[[nodiscard]] const char *file_error_name(ports::FileError error) noexcept;
} // namespace sh3::platform
