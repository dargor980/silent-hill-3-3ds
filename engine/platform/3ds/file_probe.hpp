#pragma once

#include "sh3/application/options_store.hpp"

namespace sh3::platform::ctr {
class FileProbe final {
  public:
    FileProbe(ports::IFileReader &reader, ports::IFileWriter &writer) noexcept;
    void toggle_tone() noexcept;
    void restore_defaults() noexcept;
    [[nodiscard]] bool tone_enabled() const noexcept { return options_.current().tone_enabled; }
    [[nodiscard]] ports::FileError fixture_status() const noexcept { return fixture_; }
    [[nodiscard]] ports::FileError load_status() const noexcept { return load_; }
    [[nodiscard]] ports::FileError save_status() const noexcept { return save_; }
    [[nodiscard]] bool save_attempted() const noexcept { return attempted_; }

  private:
    application::OptionsStore options_;
    ports::FileError fixture_, load_, save_{ports::FileError::ok};
    bool attempted_{false};
};
} // namespace sh3::platform::ctr
