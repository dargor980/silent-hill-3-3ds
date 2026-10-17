cmake_minimum_required(VERSION 3.21)
project(sh3_3ds VERSION 0.1.0 LANGUAGES CXX)

set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_STANDARD_REQUIRED ON)
set(CMAKE_CXX_EXTENSIONS OFF)
set(CMAKE_EXPORT_COMPILE_COMMANDS ON)
option(SH3_SANITIZERS "Enable address and undefined behavior sanitizers on host" OFF)
option(SH3_COVERAGE "Enable GCC coverage on host" OFF)
if(NINTENDO_3DS AND (SH3_SANITIZERS OR SH3_COVERAGE))
  message(FATAL_ERROR "Sanitizers and coverage are host-only")
endif()
if(SH3_SANITIZERS AND SH3_COVERAGE)
  message(FATAL_ERROR "Use separate build directories for sanitizers and coverage")
endif()

add_library(sh3_options INTERFACE)
target_compile_options(sh3_options INTERFACE -Wall -Wextra -Wpedantic -Werror)
if(SH3_SANITIZERS)
  target_compile_options(sh3_options INTERFACE -fsanitize=address,undefined -fno-omit-frame-pointer)
  target_link_options(sh3_options INTERFACE -fsanitize=address,undefined)
endif()
if(SH3_COVERAGE)
  if(NOT CMAKE_CXX_COMPILER_ID STREQUAL "GNU")
    message(FATAL_ERROR "Coverage preset requires GCC; use sanitizer preset with Clang")
  endif()
  target_compile_options(sh3_options INTERFACE --coverage -O0 -g)
  target_link_options(sh3_options INTERFACE --coverage)
endif()

add_library(sh3_domain engine/domain/lifecycle.cpp engine/domain/diagnostic_options.cpp)
target_include_directories(sh3_domain PUBLIC engine/domain/include)
target_link_libraries(sh3_domain PRIVATE sh3_options)

add_library(sh3_ports INTERFACE)
target_include_directories(sh3_ports INTERFACE engine/ports/include)
target_link_libraries(sh3_ports INTERFACE sh3_domain)

add_library(sh3_application engine/application/diagnostic_app.cpp engine/application/options_store.cpp)
target_include_directories(sh3_application PUBLIC engine/application/include)
target_link_libraries(sh3_application PUBLIC sh3_ports PRIVATE sh3_options)

add_library(sh3_diagnostics engine/platform/common/bounded_log.cpp engine/platform/common/stdio_files.cpp
  engine/platform/common/timing_window.cpp)
target_include_directories(sh3_diagnostics PUBLIC engine/platform/common/include)
target_link_libraries(sh3_diagnostics PUBLIC sh3_ports PRIVATE sh3_options)

if(NINTENDO_3DS)
  file(GLOB_RECURSE identity_inputs CONFIGURE_DEPENDS "engine/*.cpp" "engine/*.hpp")
  list(APPEND identity_inputs "${CMAKE_CURRENT_SOURCE_DIR}/CMakeLists.txt")
  set(identity "")
  foreach(source IN LISTS identity_inputs)
    file(SHA256 "${source}" source_hash)
    string(APPEND identity "${source_hash}")
  endforeach()
  string(SHA256 identity "${identity}")
  string(SUBSTRING "${identity}" 0 12 identity)
  file(GENERATE OUTPUT "${CMAKE_CURRENT_BINARY_DIR}/build-id.txt" CONTENT "${identity}\n")
  add_executable(sh3_diagnostic engine/platform/3ds/main.cpp
    engine/platform/3ds/diagnostic.cpp engine/platform/3ds/file_probe.cpp engine/platform/3ds/tone.cpp
    engine/platform/3ds/resource_probe.cpp)
  target_compile_definitions(sh3_diagnostic PRIVATE SH3_BUILD_ID="${identity}")
  target_link_libraries(sh3_diagnostic PRIVATE sh3_application sh3_diagnostics sh3_options citro2d citro3d)
  ctr_generate_smdh(OUTPUT "sh3_diagnostic.smdh" NAME "SH3 diagnostic"
    DESCRIPTION "Synthetic foundation - no game data" AUTHOR "SH3 3DS contributors")
  ctr_create_3dsx(sh3_diagnostic SMDH "${CMAKE_CURRENT_BINARY_DIR}/sh3_diagnostic.smdh")
else()
  add_executable(sh3_host engine/platform/host/main.cpp)
  target_link_libraries(sh3_host PRIVATE sh3_application sh3_diagnostics sh3_options)
endif()

include(CTest)
if(BUILD_TESTING AND NOT NINTENDO_3DS)
  foreach(suite IN ITEMS lifecycle bounded_log diagnostic_app diagnostic_options options_store stdio_files timing_window)
    add_executable(test_${suite} tests/cpp/test_${suite}.cpp)
    target_include_directories(test_${suite} PRIVATE tests/cpp)
    target_link_libraries(test_${suite} PRIVATE sh3_application sh3_diagnostics sh3_options)
    add_test(NAME ${suite} COMMAND test_${suite})
  endforeach()
  set_tests_properties(lifecycle bounded_log timing_window PROPERTIES LABELS "unit")
  set_tests_properties(diagnostic_app PROPERTIES LABELS "integration;contract")
  set_tests_properties(diagnostic_options PROPERTIES LABELS "unit")
  set_tests_properties(options_store stdio_files PROPERTIES LABELS "integration;contract" TIMEOUT 10)
  # Compile the actual 3DS composition against controlled SDK/Tone doubles on host.
  # This exercises adapter decisions and resource lifetimes, not GPU/NDSP execution.
  add_executable(test_ctr_diagnostic tests/cpp/test_ctr_diagnostic.cpp
    tests/cpp/ctr_doubles/sdk.cpp tests/cpp/ctr_doubles/resource_sdk.cpp
    engine/platform/3ds/diagnostic.cpp engine/platform/3ds/file_probe.cpp
    engine/platform/3ds/resource_probe.cpp)
  target_include_directories(test_ctr_diagnostic PRIVATE tests/cpp/ctr_doubles
    tests/cpp engine/platform/3ds)
  target_compile_definitions(test_ctr_diagnostic PRIVATE SH3_BUILD_ID="host-contract")
  target_link_libraries(test_ctr_diagnostic PRIVATE sh3_application sh3_diagnostics sh3_options)
  foreach(scenario IN ITEMS normal start_priority apt_exit hook_exit
      fail_citro3d fail_citro2d fail_target error_apt_exit frame_rejected audio_unavailable
      options_toggle options_restore options_failure fixture_invalid
      audio_alloc_failure audio_flush_failure audio_sleep_muted audio_sleep_paused audio_sleep_running
      resources_page resources_failure resources_refresh resources_sleep
      lifecycle_home_running lifecycle_home_paused lifecycle_home_muted lifecycle_duplicate_hooks
      lifecycle_exit_batch lifecycle_close_suspended lifecycle_suspended_input lifecycle_resume_keys
      lifecycle_reserved_chords lifecycle_options_home)
    add_test(NAME ctr_${scenario} COMMAND test_ctr_diagnostic ${scenario})
    set_tests_properties(ctr_${scenario} PROPERTIES LABELS "integration;contract;sdk-double"
      TIMEOUT 10)
  endforeach()
  # Exercise the actual NDSP adapter against API doubles, independently of the view.
  add_executable(test_ctr_tone tests/cpp/test_ctr_tone.cpp
    tests/cpp/ctr_doubles/audio_sdk.cpp engine/platform/3ds/tone.cpp)
  target_include_directories(test_ctr_tone PRIVATE tests/cpp/ctr_doubles
    tests/cpp engine/platform/3ds)
  target_link_libraries(test_ctr_tone PRIVATE sh3_options)
  foreach(scenario IN ITEMS normal initial_mute init_failure alloc_failure flush_failure)
    add_test(NAME tone_${scenario} COMMAND test_ctr_tone ${scenario})
    set_tests_properties(tone_${scenario} PROPERTIES LABELS "integration;contract;sdk-double;audio"
      TIMEOUT 10)
  endforeach()
  add_executable(test_ctr_resources tests/cpp/test_ctr_resources.cpp
    tests/cpp/ctr_doubles/resource_sdk.cpp engine/platform/3ds/resource_probe.cpp)
  target_include_directories(test_ctr_resources PRIVATE tests/cpp/ctr_doubles
    tests/cpp engine/platform/3ds)
  target_link_libraries(test_ctr_resources PRIVATE sh3_options)
  add_test(NAME ctr_resources COMMAND test_ctr_resources)
  set_tests_properties(ctr_resources PROPERTIES LABELS "integration;contract;sdk-double" TIMEOUT 10)
  add_test(NAME host_smoke COMMAND sh3_host)
  set_tests_properties(host_smoke PROPERTIES LABELS "smoke" PASS_REGULAR_EXPRESSION "diagnostic=passed")
endif()
