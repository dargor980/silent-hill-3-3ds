#pragma once

#include "check.hpp"
#include "sh3/domain/diagnostic_options.hpp"
#include "sh3/ports/files.hpp"
#include <algorithm>

class MemoryFiles final : public sh3::ports::IFileReader, public sh3::ports::IFileWriter {
  public:
    using E = sh3::ports::FileError;
    using Id = sh3::ports::FileId;
    std::array<sh3::ports::FileRead, 3> files{};
    E write_error{E::ok}, verify_error{E::ok};
    bool corrupt_write{false};
    bool short_verify{false};
    unsigned reads{0}, writes{0};
    Id last_write{Id::probe};
    MemoryFiles() {
        for (auto &file : files) {
            file.error = E::missing;
        }
        constexpr char fixture[] = "SH3 SD PROBE v1\n";
        files[0].error = E::ok;
        files[0].size = 16;
        std::copy_n(fixture, 16, files[0].bytes.begin());
    }
    void record(Id id, bool enabled, std::uint32_t generation) {
        const auto bytes = sh3::domain::encode_options({{enabled}, generation});
        auto &file = files[static_cast<unsigned>(id)];
        file.error = E::ok;
        file.size = bytes.size();
        std::copy(bytes.begin(), bytes.end(), file.bytes.begin());
    }
    sh3::ports::FileRead read(Id id) noexcept override {
        ++reads;
        if (writes && id == last_write && verify_error != E::ok) {
            return {verify_error};
        }
        auto result = files.at(static_cast<unsigned>(id));
        if (writes && id == last_write && short_verify) {
            result.size /= 2;
        }
        return result;
    }
    E write(Id id, const std::uint8_t *bytes, std::size_t size) noexcept override {
        CHECK(id != Id::probe && size <= 32 && bytes);
        ++writes;
        last_write = id;
        auto &file = files.at(static_cast<unsigned>(id));
        file.error = E::ok;
        file.size = write_error == E::ok ? size : size / 2;
        std::copy_n(bytes, file.size, file.bytes.begin());
        if (corrupt_write) {
            file.bytes[0] ^= 1;
        }
        return write_error;
    }
};
