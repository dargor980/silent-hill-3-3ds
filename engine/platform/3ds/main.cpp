#include "diagnostic.hpp"
#include "sh3/platform/stdio_files.hpp"

int main() {
    sh3::platform::StdioFiles files("sdmc:/3ds/sh3_diagnostic");
    return sh3::platform::ctr::run_diagnostic(files, files);
}
