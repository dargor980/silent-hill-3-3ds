cmake_minimum_required(VERSION 3.25)
project(sh3_shaderc_fixture LANGUAGES C CXX)

foreach(required IN ITEMS SH3_SHADERC_INCLUDE SH3_SHADERC_LIBRARY SH3_SPIRV_INCLUDE
                          SH3_SPIRV_HEADERS_INCLUDE SH3_SPIRV_LIBRARY)
    if(NOT ${required} OR NOT EXISTS "${${required}}")
        message(FATAL_ERROR "Set ${required} to an explicit existing dependency path")
    endif()
endforeach()
if(NOT EXISTS "${SH3_SHADERC_INCLUDE}/shaderc/shaderc.h")
    message(FATAL_ERROR "SH3_SHADERC_INCLUDE must contain the custom Shaderc headers")
endif()

# The patched recipe installs a .pc file and a dylib, without CMake exports.
add_library(Shaderc::shaderc_shared SHARED IMPORTED)
set_target_properties(Shaderc::shaderc_shared PROPERTIES
    IMPORTED_LOCATION "${SH3_SHADERC_LIBRARY}"
    INTERFACE_INCLUDE_DIRECTORIES "${SH3_SHADERC_INCLUDE}"
    INTERFACE_COMPILE_DEFINITIONS SHADERC_SHAREDLIB)
add_library(sh3_spirv_validator STATIC IMPORTED)
set_target_properties(sh3_spirv_validator PROPERTIES
    IMPORTED_LOCATION "${SH3_SPIRV_LIBRARY}"
    INTERFACE_INCLUDE_DIRECTORIES "${SH3_SPIRV_INCLUDE};${SH3_SPIRV_HEADERS_INCLUDE}")
find_package(Threads REQUIRED)

add_executable(sh3_shaderc_fixture shader.cpp)
target_link_libraries(sh3_shaderc_fixture PRIVATE Shaderc::shaderc_shared sh3_spirv_validator Threads::Threads)
target_compile_features(sh3_shaderc_fixture PRIVATE cxx_std_20)
target_compile_options(sh3_shaderc_fixture PRIVATE -Wall -Wextra -Werror)
enable_testing()
foreach(case IN ITEMS stages options errors validator debug-c debug-cpp)
    add_test(NAME shaderc-${case} COMMAND sh3_shaderc_fixture ${case} "${CMAKE_CURRENT_SOURCE_DIR}")
    set_tests_properties(shaderc-${case} PROPERTIES TIMEOUT 30)
endforeach()

if(SH3_SHADERC_SOURCE)
    add_executable(shaderc_provider_c_smoke "${SH3_SHADERC_SOURCE}/libshaderc/src/shaderc_c_smoke_test.c")
    target_link_libraries(shaderc_provider_c_smoke PRIVATE Shaderc::shaderc_shared)
    # Retain the upstream assert in Release without editing upstream source.
    target_compile_options(shaderc_provider_c_smoke PRIVATE -UNDEBUG)
    add_test(NAME shaderc-provider-c-smoke COMMAND shaderc_provider_c_smoke)
    set_tests_properties(shaderc-provider-c-smoke PROPERTIES TIMEOUT 30)
endif()
