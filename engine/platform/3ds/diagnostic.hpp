#pragma once

#include "sh3/ports/files.hpp"

namespace sh3::platform::ctr {
// Platform composition root. Returns 1 on recoverable graphics startup failure.
// All resources and hooks are released before returning to the launcher.
[[nodiscard]] int run_diagnostic(ports::IFileReader &reader, ports::IFileWriter &writer);
} // namespace sh3::platform::ctr
