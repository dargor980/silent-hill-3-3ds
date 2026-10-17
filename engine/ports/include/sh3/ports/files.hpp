#pragma once

#include <array>
#include <cstddef>
#include <cstdint>

namespace sh3::ports {
enum class FileId { probe, options_a, options_b };
enum class FileError {
    ok,
    missing,
    permission_denied,
    no_space,
    invalid_path,
    invalid_target,
    read_failed,
    too_large,
    write_failed,
    flush_failed,
    close_failed,
    invalid_data,
    verify_failed,
    ambiguous,
    generation_exhausted
};
struct FileRead {
    FileError error{FileError::ok};
    std::size_t size{0};
    std::array<std::uint8_t, 32> bytes{};
};
class IFileReader {
  public:
    virtual ~IFileReader() = default;
    // Whole-file, bounded read. Missing/oversize/I/O failures must not report ok.
    [[nodiscard]] virtual FileRead read(FileId file) noexcept = 0;
};
class IFileWriter {
  public:
    virtual ~IFileWriter() = default;
    // Synchronous close before return. Never write FileId::probe.
    // A failed call can leave a partial or complete candidate; it is not confirmed.
    [[nodiscard]] virtual FileError write(FileId file, const std::uint8_t *bytes,
                                          std::size_t size) noexcept = 0;
};
} // namespace sh3::ports
