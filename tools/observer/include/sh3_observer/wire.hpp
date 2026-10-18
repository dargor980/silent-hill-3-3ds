#pragma once
#include "sh3_observer/capture.hpp"
#include <vector>
namespace sh3::observer {
constexpr std::size_t request_bytes = 40;
constexpr std::size_t reply_header_bytes = 232;
// Framing errors do not produce an observer reply; PINE returns its own failure.
bool decode_request(const std::uint8_t*, std::size_t, Request&) noexcept;
std::vector<std::uint8_t> encode_reply(const Result&);
} // namespace sh3::observer
