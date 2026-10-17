#pragma once

#include "sh3/domain/diagnostic_options.hpp"
#include "sh3/ports/files.hpp"

namespace sh3::application {
class OptionsStore final {
  public:
    OptionsStore(ports::IFileReader &reader, ports::IFileWriter &writer) noexcept;
    [[nodiscard]] ports::FileError load() noexcept;
    [[nodiscard]] ports::FileError save(domain::DiagnosticOptions options) noexcept;
    [[nodiscard]] domain::DiagnosticOptions current() const noexcept { return current_.options; }
    [[nodiscard]] std::uint32_t generation() const noexcept { return current_.generation; }

  private:
    ports::IFileReader &reader_;
    ports::IFileWriter &writer_;
    domain::OptionsRecord current_{};
    ports::FileId active_{ports::FileId::options_b};
    ports::FileError write_block_{ports::FileError::read_failed};
};
} // namespace sh3::application
