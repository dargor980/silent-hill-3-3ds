#include "file_probe.hpp"
#include <algorithm>
#include <array>

namespace sh3::platform::ctr {
FileProbe::FileProbe(ports::IFileReader &reader, ports::IFileWriter &writer) noexcept
    : options_(reader, writer) {
    constexpr std::array<std::uint8_t, 16> expected{'S', 'H', '3', ' ', 'S', 'D', ' ', 'P',
                                                    'R', 'O', 'B', 'E', ' ', 'v', '1', '\n'};
    const auto read = reader.read(ports::FileId::probe);
    fixture_ = read.error;
    if (fixture_ == ports::FileError::ok &&
        (read.size != expected.size() ||
         !std::equal(expected.begin(), expected.end(), read.bytes.begin()))) {
        fixture_ = ports::FileError::invalid_data;
    }
    load_ = options_.load();
}
void FileProbe::toggle_tone() noexcept {
    attempted_ = true;
    save_ = options_.save({!options_.current().tone_enabled});
}
void FileProbe::restore_defaults() noexcept {
    attempted_ = true;
    save_ = options_.save({});
}
} // namespace sh3::platform::ctr
