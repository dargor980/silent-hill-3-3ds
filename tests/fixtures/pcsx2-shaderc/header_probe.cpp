#include <shaderc/shaderc.hpp>

#ifndef SHADERC_PCSX2_CUSTOM
#error Expected the fixed PCSX2 custom Shaderc API
#endif

void check_custom_header(shaderc::CompileOptions& options) {
    options.SetGenerateDebugInfo(true, false);
}
