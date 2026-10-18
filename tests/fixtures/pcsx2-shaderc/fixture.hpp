#pragma once

#include <shaderc/shaderc.h>
#include <spirv-tools/libspirv.h>
#include <spirv/unified1/spirv.h>

#include <cstring>
#include <fstream>
#include <iterator>
#include <memory>
#include <stdexcept>
#include <string>
#include <type_traits>
#include <vector>

#ifndef SHADERC_PCSX2_CUSTOM
#error Expected the fixed PCSX2 custom Shaderc API
#endif

namespace fixture {
inline void require(bool passed, const char* message) {
    if (!passed) throw std::runtime_error(message);
}

template<class T, void (*Release)(T)>
using Handle = std::unique_ptr<std::remove_pointer_t<T>, decltype(Release)>;
using Compiler = Handle<shaderc_compiler_t, shaderc_compiler_release>;
using Options = Handle<shaderc_compile_options_t, shaderc_compile_options_release>;
using Result = Handle<shaderc_compilation_result_t, shaderc_result_release>;

inline std::string read_file(std::string const& path) {
    std::ifstream input(path, std::ios::binary);
    require(input.good(), "cannot read own shader");
    return {std::istreambuf_iterator<char>(input), std::istreambuf_iterator<char>()};
}

inline Options options(const char* shade = "0.75") {
    Options result(shaderc_compile_options_initialize(), shaderc_compile_options_release);
    require(result != nullptr, "options allocation");
    shaderc_compile_options_set_target_env(result.get(), shaderc_target_env_vulkan, shaderc_env_version_vulkan_1_0);
    shaderc_compile_options_set_target_spirv(result.get(), shaderc_spirv_version_1_0);
    shaderc_compile_options_add_macro_definition(result.get(), "SHADE", 5, shade, std::strlen(shade));
    return result;
}

inline Result compile(shaderc_compiler_t compiler, std::string const& source,
                      shaderc_shader_kind kind, shaderc_compile_options_t opts) {
    Result result(shaderc_compile_into_spv(compiler, source.data(), source.size(), kind,
                  "own-fixture.glsl", "main", opts), shaderc_result_release);
    require(result != nullptr, "result allocation");
    return result;
}

inline std::vector<uint32_t> binary(shaderc_compilation_result_t result) {
    require(shaderc_result_get_compilation_status(result) == shaderc_compilation_status_success,
            shaderc_result_get_error_message(result));
    require(shaderc_result_get_num_errors(result) == 0, "successful result with errors");
    const auto bytes = shaderc_result_get_length(result);
    require(bytes >= 20 && bytes % sizeof(uint32_t) == 0, "SPIR-V word alignment/size");
    std::vector<uint32_t> words(bytes / sizeof(uint32_t));
    std::memcpy(words.data(), shaderc_result_get_bytes(result), bytes);
    return words;
}

inline void validate(std::vector<uint32_t> const& words, bool expected_valid = true) {
    Handle<spv_context, spvContextDestroy> context(spvContextCreate(SPV_ENV_VULKAN_1_0), spvContextDestroy);
    require(context != nullptr, "validator context allocation");
    spv_diagnostic raw = nullptr;
    auto status = spvValidateBinary(context.get(), words.data(), words.size(), &raw);
    Handle<spv_diagnostic, spvDiagnosticDestroy> diagnostic(raw, spvDiagnosticDestroy);
    if (expected_valid) {
        require(status == SPV_SUCCESS, diagnostic ? diagnostic->error : "SPIR-V validation failed");
    } else {
        require(status != SPV_SUCCESS, "invalid SPIR-V accepted");
        require(diagnostic && diagnostic->error && diagnostic->error[0], "missing validator diagnostic");
    }
}

struct ModuleInfo {
    unsigned entry_points = 0;
    uint32_t execution_model = ~uint32_t{0};
    bool debug_line = false;
    bool nonsemantic_debug = false;
};

inline ModuleInfo inspect(std::vector<uint32_t> const& words) {
    validate(words);
    require(words.size() >= 5 && words[0] == SpvMagicNumber, "SPIR-V magic");
    require(words[1] == 0x00010000 && words[3] > 0 && words[4] == 0, "SPIR-V 1.0 header");
    ModuleInfo info;
    for (std::size_t index = 5; index < words.size();) {
        auto count = words[index] >> 16;
        auto opcode = words[index] & 0xffff;
        require(count > 0 && count <= words.size() - index, "instruction bounds");
        if (opcode == SpvOpEntryPoint) {
            require(count >= 4, "entry point operands");
            ++info.entry_points;
            info.execution_model = words[index + 1];
        }
        if (opcode == SpvOpLine) info.debug_line = true;
        if (opcode == SpvOpExtInstImport) {
            require(count >= 3, "import operands");
            auto text = reinterpret_cast<const char*>(words.data() + index + 2);
            const auto capacity = (count - 2) * sizeof(uint32_t);
            const auto end = static_cast<const char*>(std::memchr(text, '\0', capacity));
            require(end != nullptr, "unterminated import name");
            if (std::string(text, end).starts_with("NonSemantic.Shader.DebugInfo."))
                info.nonsemantic_debug = true;
        }
        index += count;
    }
    require(info.entry_points == 1, "single entry point");
    return info;
}
} // namespace fixture
