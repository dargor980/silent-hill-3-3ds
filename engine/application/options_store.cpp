#include "sh3/application/options_store.hpp"
#include <algorithm>
#include <limits>

namespace sh3::application {
namespace {
using E = ports::FileError;
E decode(const ports::FileRead &read, domain::OptionsRecord &record) noexcept {
    if (read.error != E::ok) {
        return read.error;
    }
    return domain::decode_options(read.bytes.data(), read.size, record) ? E::ok : E::invalid_data;
}
bool uncertain(E error) noexcept {
    return error != E::ok && error != E::missing && error != E::invalid_data &&
           error != E::too_large;
}
} // namespace
OptionsStore::OptionsStore(ports::IFileReader &reader, ports::IFileWriter &writer) noexcept
    : reader_(reader), writer_(writer) {}

ports::FileError OptionsStore::load() noexcept {
    domain::OptionsRecord a, b;
    const auto ea = decode(reader_.read(ports::FileId::options_a), a);
    const auto eb = decode(reader_.read(ports::FileId::options_b), b);
    // An unreadable slot may contain a newer generation. Do not overwrite either.
    if (uncertain(ea) || uncertain(eb)) {
        write_block_ = uncertain(ea) ? ea : eb;
        return write_block_;
    }
    if (ea == E::ok && eb == E::ok && a.generation == b.generation &&
        a.options.tone_enabled != b.options.tone_enabled) {
        write_block_ = E::ambiguous;
        return write_block_;
    }
    write_block_ = E::ok;
    if (ea == E::ok && (eb != E::ok || a.generation >= b.generation)) {
        current_ = a;
        active_ = ports::FileId::options_a;
    } else if (eb == E::ok) {
        current_ = b;
        active_ = ports::FileId::options_b;
    } else {
        current_ = {};
        active_ = ports::FileId::options_b;
    }
    if (ea != E::ok && ea != E::missing) {
        return ea;
    }
    if (eb != E::ok && eb != E::missing) {
        return eb;
    }
    return current_.generation == 0 ? E::missing : E::ok;
}

ports::FileError OptionsStore::save(domain::DiagnosticOptions options) noexcept {
    if (write_block_ != E::ok) {
        return write_block_;
    }
    if (current_.generation == std::numeric_limits<std::uint32_t>::max()) {
        return E::generation_exhausted;
    }
    const auto target =
        active_ == ports::FileId::options_a ? ports::FileId::options_b : ports::FileId::options_a;
    const domain::OptionsRecord next{options, current_.generation + 1};
    const auto bytes = domain::encode_options(next);
    const auto error = writer_.write(target, bytes.data(), bytes.size());
    if (error != E::ok) {
        return error;
    }
    const auto verify = reader_.read(target);
    if (verify.error != E::ok) {
        return verify.error;
    }
    if (verify.size != bytes.size() ||
        !std::equal(bytes.begin(), bytes.end(), verify.bytes.begin())) {
        return E::verify_failed;
    }
    current_ = next;
    active_ = target;
    return E::ok;
}
} // namespace sh3::application
