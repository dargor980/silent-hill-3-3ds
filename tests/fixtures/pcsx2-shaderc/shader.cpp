#include "fixture.hpp"
#include <shaderc/shaderc.hpp>

#include <iostream>
#include <utility>

using namespace fixture;

namespace {
void stages(shaderc_compiler_t compiler, std::string const& vertex, std::string const& fragment) {
    auto opts = options();
    auto vert = compile(compiler, vertex, shaderc_vertex_shader, opts.get());
    auto frag = compile(compiler, fragment, shaderc_fragment_shader, opts.get());
    require(inspect(binary(vert.get())).execution_model == SpvExecutionModelVertex, "vertex execution model");
    require(inspect(binary(frag.get())).execution_model == SpvExecutionModelFragment, "fragment execution model");
}

void option_effects(shaderc_compiler_t compiler, std::string const& fragment) {
    auto first = options("0.75");
    auto second = options("0.125");
    for (auto const& entry : {std::pair{first.get(), "0.75"}, std::pair{second.get(), "0.125"}}) {
        Result preprocessed(shaderc_compile_into_preprocessed_text(compiler, fragment.data(), fragment.size(),
                            shaderc_fragment_shader, "own-fixture.frag", "main", entry.first), shaderc_result_release);
        require(preprocessed != nullptr, "preprocessor allocation");
        require(shaderc_result_get_compilation_status(preprocessed.get()) == shaderc_compilation_status_success,
                "preprocessing failed");
        std::string text(shaderc_result_get_bytes(preprocessed.get()), shaderc_result_get_length(preprocessed.get()));
        require(text.find(entry.second) != std::string::npos && text.find("SHADE") == std::string::npos,
                "macro expansion");
    }
    auto normal = compile(compiler, fragment, shaderc_fragment_shader, first.get());
    auto changed = compile(compiler, fragment, shaderc_fragment_shader, second.get());
    auto normal_words = binary(normal.get());
    auto changed_words = binary(changed.get());
    inspect(normal_words);
    inspect(changed_words);
    require(normal_words != changed_words, "macro must change module");
    shaderc_compile_options_set_optimization_level(second.get(), shaderc_optimization_level_performance);
    auto optimized = compile(compiler, fragment, shaderc_fragment_shader, second.get());
    auto optimized_words = binary(optimized.get());
    inspect(optimized_words);
    require(changed_words != optimized_words, "optimization must change this module");
}

void errors(shaderc_compiler_t compiler, std::string const& vertex) {
    auto opts = options();
    for (auto const& source : {std::string("#version 450\nvoid main() { this is invalid; }\n"), vertex}) {
        auto result = compile(compiler, source, shaderc_fragment_shader, opts.get());
        require(shaderc_result_get_compilation_status(result.get()) == shaderc_compilation_status_compilation_error,
                "expected GLSL/incorrect-stage compilation error");
        require(shaderc_result_get_num_errors(result.get()) > 0, "error count");
        require(shaderc_result_get_error_message(result.get())[0] != '\0', "empty compiler diagnostic");
        require(shaderc_result_get_length(result.get()) == 0, "unexpected output on error");
    }
    auto recovered = compile(compiler, vertex, shaderc_vertex_shader, opts.get());
    inspect(binary(recovered.get()));
}

void validator_errors(shaderc_compiler_t compiler, std::string const& vertex) {
    auto opts = options();
    auto result = compile(compiler, vertex, shaderc_vertex_shader, opts.get());
    auto words = binary(result.get());
    inspect(words);
    auto truncated = words;
    truncated.pop_back();
    validate(truncated, false);
    auto corrupted = words;
    corrupted[0] = 0;
    validate(corrupted, false);
    validate(words);
}

void debug_c(shaderc_compiler_t compiler, std::string const& vertex) {
    for (int mode = 0; mode < 3; ++mode) {
        auto opts = options();
        shaderc_compile_options_set_generate_debug_info(opts.get(), mode != 0, mode == 2);
        auto result = compile(compiler, vertex, shaderc_vertex_shader, opts.get());
        auto info = inspect(binary(result.get()));
        require(info.nonsemantic_debug == (mode == 2), "C nonsemantic debug option");
        if (mode == 0) require(!info.debug_line, "unexpected debug lines");
        if (mode == 1) require(info.debug_line, "missing conventional debug lines");
    }
}

void debug_cpp(std::string const& vertex) {
    shaderc::Compiler compiler;
    require(compiler.IsValid(), "C++ compiler initialization");
    for (bool nonsemantic : {false, true}) {
        shaderc::CompileOptions opts;
        opts.SetTargetEnvironment(shaderc_target_env_vulkan, shaderc_env_version_vulkan_1_0);
        opts.SetTargetSpirv(shaderc_spirv_version_1_0);
        opts.SetGenerateDebugInfo(true, nonsemantic);
        auto result = compiler.CompileGlslToSpv(vertex, shaderc_vertex_shader, "own-fixture.vert", opts);
        require(result.GetCompilationStatus() == shaderc_compilation_status_success, "C++ compile failure");
        std::vector<uint32_t> words(result.cbegin(), result.cend());
        require(inspect(words).nonsemantic_debug == nonsemantic, "C++ custom debug forwarding");
    }
}
} // namespace

int main(int argc, char** argv) {
    try {
        require(argc == 3, "usage: fixture case own-shader-directory");
        auto vertex = read_file(std::string(argv[2]) + "/vertex.vert");
        auto fragment = read_file(std::string(argv[2]) + "/fragment.frag");
        Compiler compiler(shaderc_compiler_initialize(), shaderc_compiler_release);
        require(compiler != nullptr, "C compiler initialization");
        std::string selected = argv[1];
        if (selected == "stages") stages(compiler.get(), vertex, fragment);
        else if (selected == "options") option_effects(compiler.get(), fragment);
        else if (selected == "errors") errors(compiler.get(), vertex);
        else if (selected == "validator") validator_errors(compiler.get(), vertex);
        else if (selected == "debug-c") debug_c(compiler.get(), vertex);
        else if (selected == "debug-cpp") debug_cpp(vertex);
        else throw std::runtime_error("unknown case");
        std::cout << selected << ": passed\n";
        return 0;
    } catch (std::exception const& error) {
        std::cerr << error.what() << '\n';
        return 1;
    }
}
