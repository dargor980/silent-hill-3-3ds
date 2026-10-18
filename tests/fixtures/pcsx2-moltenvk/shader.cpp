#include <shaderc/shaderc.hpp>
#include <fstream>
#include <iostream>

int main(int argc, char** argv) {
    if (argc != 2) return 2;
    constexpr auto source = R"(#version 450
layout(local_size_x=32) in;
layout(set=0,binding=0,std430) buffer Values { uint data[]; } values;
void main() { uint i=gl_GlobalInvocationID.x; values.data[i]=values.data[i]*3u+7u; }
)";
    shaderc::Compiler compiler;
    shaderc::CompileOptions options;
    options.SetTargetEnvironment(shaderc_target_env_vulkan, shaderc_env_version_vulkan_1_1);
    auto result = compiler.CompileGlslToSpv(source, shaderc_compute_shader, "own-compute.comp", options);
    if (result.GetCompilationStatus() != shaderc_compilation_status_success) {
        std::cerr << result.GetErrorMessage(); return 1;
    }
    std::ofstream output(argv[1], std::ios::binary);
    for (uint32_t word : result) output.write(reinterpret_cast<const char*>(&word), sizeof word);
    return output ? 0 : 1;
}
