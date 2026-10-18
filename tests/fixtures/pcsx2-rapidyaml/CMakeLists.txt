cmake_minimum_required(VERSION 3.25)
project(sh3_rapidyaml_fixture LANGUAGES CXX)

# The build exports targets directly; installed consumption must use its package.
if(SH3_RYML_BUILD_DIR)
    if(NOT EXISTS "${SH3_RYML_BUILD_DIR}/rymlTargets.cmake")
        message(FATAL_ERROR "Set SH3_RYML_BUILD_DIR to the explicit build exports")
    endif()
    include("${SH3_RYML_BUILD_DIR}/rymlTargets.cmake")
else()
    if(NOT SH3_RYML_CONFIG_DIR OR NOT EXISTS "${SH3_RYML_CONFIG_DIR}/rymlConfig.cmake")
        message(FATAL_ERROR "Set SH3_RYML_CONFIG_DIR to the explicit RapidYAML package")
    endif()
    set(ryml_DIR "${SH3_RYML_CONFIG_DIR}")
    find_package(ryml 0.12.1 EXACT CONFIG REQUIRED PATHS "${SH3_RYML_CONFIG_DIR}" NO_DEFAULT_PATH)
endif()

add_executable(sh3_rapidyaml_fixture yaml.cpp)
target_link_libraries(sh3_rapidyaml_fixture PRIVATE ryml::ryml)
target_compile_features(sh3_rapidyaml_fixture PRIVATE cxx_std_20)
target_compile_options(sh3_rapidyaml_fixture PRIVATE -Wall -Wextra -Werror)
enable_testing()
foreach(case IN ITEMS structure ownership roundtrip bounds invalid)
    add_test(NAME rapidyaml-${case} COMMAND sh3_rapidyaml_fixture ${case}
        "${CMAKE_CURRENT_SOURCE_DIR}/config.yaml")
    set_tests_properties(rapidyaml-${case} PROPERTIES TIMEOUT 15)
endforeach()

# Compile original sources without fetching the full upstream test dependency tree.
if(SH3_RYML_SOURCE)
    add_executable(ryml_provider_quickstart "${SH3_RYML_SOURCE}/samples/quickstart.cpp")
    add_executable(ryml_provider_quickstart_ints
        "${SH3_RYML_SOURCE}/samples/quickstart-ints.cpp"
        "${SH3_RYML_SOURCE}/src_extra/c4/yml/extra/event_handler_ints.cpp"
        "${SH3_RYML_SOURCE}/src_extra/c4/yml/extra/ints_utils.cpp")
    target_include_directories(ryml_provider_quickstart_ints PRIVATE "${SH3_RYML_SOURCE}/src_extra")
    foreach(target IN ITEMS ryml_provider_quickstart ryml_provider_quickstart_ints)
        target_link_libraries(${target} PRIVATE ryml::ryml)
        target_compile_features(${target} PRIVATE cxx_std_20)
        file(MAKE_DIRECTORY "${CMAKE_CURRENT_BINARY_DIR}/${target}-work")
        add_test(NAME ${target} COMMAND ${target})
        set_tests_properties(${target} PROPERTIES TIMEOUT 60
            WORKING_DIRECTORY "${CMAKE_CURRENT_BINARY_DIR}/${target}-work")
    endforeach()
endif()
