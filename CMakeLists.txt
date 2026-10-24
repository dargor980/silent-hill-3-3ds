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
  # Observer tests exercise real threads; non-atomic counters can corrupt gcov data.
  target_compile_options(sh3_options INTERFACE --coverage -fprofile-update=atomic -O0 -g)
  target_link_options(sh3_options INTERFACE --coverage)
endif()

add_library(sh3_domain engine/domain/lifecycle.cpp engine/domain/diagnostic_options.cpp
  engine/domain/render_scene.cpp engine/domain/animation_pose.cpp engine/domain/character_skinning.cpp
  engine/domain/character_lighting.cpp engine/domain/character_world.cpp engine/domain/inspection_rig.cpp)
target_include_directories(sh3_domain PUBLIC engine/domain/include)
target_link_libraries(sh3_domain PRIVATE sh3_options)

add_library(sh3_ports INTERFACE)
target_include_directories(sh3_ports INTERFACE engine/ports/include)
target_link_libraries(sh3_ports INTERFACE sh3_domain)

add_library(sh3_application engine/application/diagnostic_app.cpp engine/application/options_store.cpp
  engine/application/render_probe.cpp engine/application/animation_probe.cpp engine/application/rig_probe.cpp)
target_include_directories(sh3_application PUBLIC engine/application/include)
target_link_libraries(sh3_application PUBLIC sh3_ports PRIVATE sh3_options)

add_library(sh3_diagnostics engine/platform/common/bounded_log.cpp engine/platform/common/stdio_files.cpp
  engine/platform/common/timing_window.cpp engine/platform/common/checker_texture.cpp
  engine/platform/common/inspection_texture.cpp engine/platform/common/inspection_geometry.cpp
  engine/platform/common/inspection_crc32.cpp engine/platform/common/inspection_animation.cpp
  engine/platform/common/inspection_character.cpp engine/platform/common/inspection_character_material.cpp
  engine/platform/common/inspection_character_lighting.cpp engine/platform/common/inspection_character_world.cpp
  engine/platform/common/inspection_rig.cpp)
target_include_directories(sh3_diagnostics PUBLIC engine/platform/common/include)
target_link_libraries(sh3_diagnostics PUBLIC sh3_ports PRIVATE sh3_options)

if(NINTENDO_3DS)
  enable_language(ASM)
  find_package(Python3 REQUIRED COMPONENTS Interpreter)
  function(sh3_add_inspection_shader target source)
    ctr_add_shader_library(${target} ${source})
    dkp_add_embedded_binary_library(${target}_data ${target})
    # Inspect the actual assembler output before embedding it in any executable.
    add_custom_target(${target}_output_check
      COMMAND "${Python3_EXECUTABLE}" "${CMAKE_CURRENT_SOURCE_DIR}/tools/qa/pica_shader_outputs.py"
        "${CMAKE_CURRENT_BINARY_DIR}/${target}.shbin"
      DEPENDS ${target} "${CMAKE_CURRENT_SOURCE_DIR}/tools/qa/pica_shader_outputs.py"
      VERBATIM)
    add_dependencies(${target}_data ${target}_output_check)
  endfunction()
  file(GLOB_RECURSE identity_inputs CONFIGURE_DEPENDS "engine/*.cpp" "engine/*.hpp" "engine/*.pica")
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
  sh3_add_inspection_shader(scene_shader engine/platform/3ds/render/scene.v.pica)
  add_executable(sh3_render_probe engine/platform/3ds/render/main.cpp
    engine/platform/3ds/render/renderer.cpp engine/platform/3ds/render/material_state.cpp)
  target_compile_definitions(sh3_render_probe PRIVATE SH3_BUILD_ID="${identity}")
  target_link_libraries(sh3_render_probe PRIVATE sh3_application sh3_diagnostics
    sh3_options scene_shader_data citro3d)
  ctr_generate_smdh(OUTPUT "sh3_render_probe.smdh" NAME "SH3 synthetic 3D"
    DESCRIPTION "Synthetic room - no game data" AUTHOR "SH3 3DS contributors")
  ctr_create_3dsx(sh3_render_probe SMDH "${CMAKE_CURRENT_BINARY_DIR}/sh3_render_probe.smdh")
  add_executable(sh3_texture_probe engine/platform/3ds/render/main.cpp
    engine/platform/3ds/render/renderer.cpp engine/platform/3ds/render/material_state.cpp)
  target_compile_definitions(sh3_texture_probe PRIVATE
    SH3_BUILD_ID="${identity}" SH3_TEXTURE_INSPECTION=1)
  target_link_libraries(sh3_texture_probe PRIVATE sh3_application sh3_diagnostics
    sh3_options scene_shader_data citro3d)
  ctr_generate_smdh(OUTPUT "sh3_texture_probe.smdh" NAME "SH3 texture inspection"
    DESCRIPTION "Private SD texture - own panel" AUTHOR "SH3 3DS contributors")
  ctr_create_3dsx(sh3_texture_probe SMDH "${CMAKE_CURRENT_BINARY_DIR}/sh3_texture_probe.smdh")
  add_executable(sh3_geometry_probe engine/platform/3ds/render/main.cpp
    engine/platform/3ds/render/renderer.cpp engine/platform/3ds/render/material_state.cpp)
  target_compile_definitions(sh3_geometry_probe PRIVATE
    SH3_BUILD_ID="${identity}" SH3_GEOMETRY_INSPECTION=1)
  target_link_libraries(sh3_geometry_probe PRIVATE sh3_application sh3_diagnostics
    sh3_options scene_shader_data citro3d)
  ctr_generate_smdh(OUTPUT "sh3_geometry_probe.smdh" NAME "SH3 geometry inspection"
    DESCRIPTION "Private SD mesh - diagnostic material" AUTHOR "SH3 3DS contributors")
  ctr_create_3dsx(sh3_geometry_probe SMDH "${CMAKE_CURRENT_BINARY_DIR}/sh3_geometry_probe.smdh")
  add_executable(sh3_material_probe engine/platform/3ds/render/main.cpp
    engine/platform/3ds/render/renderer.cpp engine/platform/3ds/render/material_state.cpp)
  target_compile_definitions(sh3_material_probe PRIVATE
    SH3_BUILD_ID="${identity}" SH3_MATERIAL_INSPECTION=1)
  target_link_libraries(sh3_material_probe PRIVATE sh3_application sh3_diagnostics
    sh3_options scene_shader_data citro3d)
  ctr_generate_smdh(OUTPUT "sh3_material_probe.smdh" NAME "SH3 material inspection"
    DESCRIPTION "Private glass material - inspection view" AUTHOR "SH3 3DS contributors")
  ctr_create_3dsx(sh3_material_probe SMDH "${CMAKE_CURRENT_BINARY_DIR}/sh3_material_probe.smdh")
  add_executable(sh3_animation_probe engine/platform/3ds/render/animation_main.cpp
    engine/platform/3ds/render/renderer.cpp engine/platform/3ds/render/material_state.cpp)
  target_compile_definitions(sh3_animation_probe PRIVATE SH3_BUILD_ID="${identity}")
  target_link_libraries(sh3_animation_probe PRIVATE sh3_application sh3_diagnostics
    sh3_options scene_shader_data citro3d)
  ctr_generate_smdh(OUTPUT "sh3_animation_probe.smdh" NAME "SH3 animation inspection"
    DESCRIPTION "Private clip 0x1449 - skeleton axes" AUTHOR "SH3 3DS contributors")
  ctr_create_3dsx(sh3_animation_probe SMDH "${CMAKE_CURRENT_BINARY_DIR}/sh3_animation_probe.smdh")
  sh3_add_inspection_shader(character_shader engine/platform/3ds/render/character.v.pica)
  add_executable(sh3_heather_probe engine/platform/3ds/render/rig_main.cpp
    engine/platform/3ds/render/rig_renderer.cpp engine/platform/3ds/render/material_state.cpp)
  target_compile_definitions(sh3_heather_probe PRIVATE SH3_BUILD_ID="${identity}")
  target_link_libraries(sh3_heather_probe PRIVATE sh3_application sh3_diagnostics
    sh3_options character_shader_data citro3d)
  ctr_generate_smdh(OUTPUT "sh3_heather_probe.smdh" NAME "SH3 Heather original"
    DESCRIPTION "Private original outfit - skeletal inspection" AUTHOR "SH3 3DS contributors")
  ctr_create_3dsx(sh3_heather_probe SMDH "${CMAKE_CURRENT_BINARY_DIR}/sh3_heather_probe.smdh")
  add_executable(sh3_character_probe engine/platform/3ds/render/character_main.cpp
    engine/platform/3ds/render/character_renderer.cpp engine/platform/3ds/render/material_state.cpp)
  target_compile_definitions(sh3_character_probe PRIVATE SH3_BUILD_ID="${identity}")
  target_link_libraries(sh3_character_probe PRIVATE sh3_application sh3_diagnostics
    sh3_options character_shader_data citro3d)
  ctr_generate_smdh(OUTPUT "sh3_character_probe.smdh" NAME "SH3 character inspection"
    DESCRIPTION "Private animated mesh - inspection shading" AUTHOR "SH3 3DS contributors")
  ctr_create_3dsx(sh3_character_probe SMDH "${CMAKE_CURRENT_BINARY_DIR}/sh3_character_probe.smdh")
  add_executable(sh3_character_material_probe engine/platform/3ds/render/character_main.cpp
    engine/platform/3ds/render/character_renderer.cpp engine/platform/3ds/render/material_state.cpp)
  target_compile_definitions(sh3_character_material_probe PRIVATE SH3_BUILD_ID="${identity}" SH3_CHARACTER_MATERIAL=1)
  target_link_libraries(sh3_character_material_probe PRIVATE sh3_application sh3_diagnostics
    sh3_options character_shader_data citro3d)
  ctr_generate_smdh(OUTPUT "sh3_character_material_probe.smdh" NAME "SH3 textured character"
    DESCRIPTION "Private animated mesh - captured textures" AUTHOR "SH3 3DS contributors")
  ctr_create_3dsx(sh3_character_material_probe SMDH "${CMAKE_CURRENT_BINARY_DIR}/sh3_character_material_probe.smdh")
  add_executable(sh3_character_lighting_probe engine/platform/3ds/render/character_main.cpp
    engine/platform/3ds/render/character_renderer.cpp engine/platform/3ds/render/material_state.cpp)
  target_compile_definitions(sh3_character_lighting_probe PRIVATE SH3_BUILD_ID="${identity}" SH3_CHARACTER_LIGHTING=1)
  target_link_libraries(sh3_character_lighting_probe PRIVATE sh3_application sh3_diagnostics
    sh3_options character_shader_data citro3d)
  ctr_generate_smdh(OUTPUT "sh3_character_lighting_probe.smdh" NAME "SH3 captured lighting"
    DESCRIPTION "Private animated mesh - fixed captured lights" AUTHOR "SH3 3DS contributors")
  ctr_create_3dsx(sh3_character_lighting_probe SMDH "${CMAKE_CURRENT_BINARY_DIR}/sh3_character_lighting_probe.smdh")
  add_executable(sh3_character_world_probe engine/platform/3ds/render/character_main.cpp
    engine/platform/3ds/render/character_renderer.cpp engine/platform/3ds/render/material_state.cpp)
  target_compile_definitions(sh3_character_world_probe PRIVATE SH3_BUILD_ID="${identity}" SH3_CHARACTER_WORLD=1)
  target_link_libraries(sh3_character_world_probe PRIVATE sh3_application sh3_diagnostics
    sh3_options character_shader_data citro3d)
  ctr_generate_smdh(OUTPUT "sh3_character_world_probe.smdh" NAME "SH3 world placement"
    DESCRIPTION "Fixed placements - private resources" AUTHOR "SH3 3DS contributors")
  ctr_create_3dsx(sh3_character_world_probe SMDH "${CMAKE_CURRENT_BINARY_DIR}/sh3_character_world_probe.smdh")
else()
  add_executable(sh3_host engine/platform/host/main.cpp)
  target_link_libraries(sh3_host PRIVATE sh3_application sh3_diagnostics sh3_options)
endif()

include(CTest)
if(BUILD_TESTING AND NOT NINTENDO_3DS)
  add_executable(test_inspection_rig tests/cpp/test_inspection_rig.cpp)
  target_include_directories(test_inspection_rig PRIVATE tests/cpp)
  target_link_libraries(test_inspection_rig PRIVATE sh3_application sh3_diagnostics sh3_options)
  add_test(NAME inspection_rig COMMAND test_inspection_rig)
  set_tests_properties(inspection_rig PROPERTIES LABELS "unit;contract;render" TIMEOUT 10)
  add_executable(test_ctr_rig tests/cpp/test_ctr_rig.cpp tests/cpp/render_doubles/sdk.cpp
    engine/platform/3ds/render/rig_renderer.cpp engine/platform/3ds/render/material_state.cpp)
  target_include_directories(test_ctr_rig PRIVATE tests/cpp/render_doubles tests/cpp engine/platform/3ds/render)
  target_link_libraries(test_ctr_rig PRIVATE sh3_application sh3_diagnostics sh3_options)
  foreach(scenario IN ITEMS normal invalid busy flush draw init_CITRO3D init_TARGET init_SHADER
      init_EMPTY_SHADER init_PROGRAM init_VERTEX_SHADER init_UNIFORM init_VERTICES
      init_ATTRIBUTES_0 init_ATTRIBUTES_1 init_ATTRIBUTES_2 init_BUFFER
      init_TEXTURE_READ_0 init_TEXTURE_READ_12 init_TEXTURE_0 init_TEXTURE_12
      init_TEXTURE_FLUSH_0 init_TEXTURE_FLUSH_12)
    add_test(NAME rig_gpu_${scenario} COMMAND test_ctr_rig ${scenario})
    set_tests_properties(rig_gpu_${scenario} PROPERTIES LABELS "integration;contract;sdk-double;render" TIMEOUT 15)
  endforeach()
  add_executable(test_character_lighting tests/cpp/test_character_lighting.cpp)
  add_executable(test_character_world tests/cpp/test_character_world.cpp)
  target_include_directories(test_character_world PRIVATE tests/cpp)
  target_link_libraries(test_character_world PRIVATE sh3_diagnostics sh3_options)
  add_test(NAME character_world COMMAND test_character_world)
  set_tests_properties(character_world PROPERTIES LABELS "unit;contract;render" TIMEOUT 15)
  target_include_directories(test_character_lighting PRIVATE tests/cpp)
  target_link_libraries(test_character_lighting PRIVATE sh3_diagnostics sh3_options)
  add_test(NAME character_lighting COMMAND test_character_lighting)
  set_tests_properties(character_lighting PROPERTIES LABELS "unit;contract;render" TIMEOUT 10)
  add_executable(test_character_skinning tests/cpp/test_character_skinning.cpp)
  target_include_directories(test_character_skinning PRIVATE tests/cpp)
  target_link_libraries(test_character_skinning PRIVATE sh3_application sh3_diagnostics sh3_options)
  add_test(NAME character_skinning COMMAND test_character_skinning)
  set_tests_properties(character_skinning PROPERTIES LABELS "unit;contract;render" TIMEOUT 10)
  add_executable(test_ctr_character tests/cpp/test_ctr_character.cpp tests/cpp/render_doubles/sdk.cpp
    engine/platform/3ds/render/character_renderer.cpp engine/platform/3ds/render/material_state.cpp)
  target_include_directories(test_ctr_character PRIVATE tests/cpp/render_doubles tests/cpp engine/platform/3ds/render)
  target_link_libraries(test_ctr_character PRIVATE sh3_application sh3_diagnostics sh3_options)
  foreach(scenario IN ITEMS normal invalid busy flush draw init_CITRO3D init_TARGET init_SHADER
      init_EMPTY_SHADER init_PROGRAM init_VERTEX_SHADER init_UNIFORM init_VERTICES
      init_ATTRIBUTES_0 init_ATTRIBUTES_1 init_ATTRIBUTES_2 init_BUFFER)
    add_test(NAME character_gpu_${scenario} COMMAND test_ctr_character ${scenario})
    set_tests_properties(character_gpu_${scenario} PROPERTIES LABELS "integration;contract;sdk-double;render" TIMEOUT 10)
  endforeach()
  add_executable(test_character_material tests/cpp/test_character_material.cpp)
  target_include_directories(test_character_material PRIVATE tests/cpp)
  target_link_libraries(test_character_material PRIVATE sh3_diagnostics sh3_options)
  add_test(NAME character_material COMMAND test_character_material)
  add_executable(test_ctr_character_material tests/cpp/test_ctr_character_material.cpp tests/cpp/render_doubles/sdk.cpp
    engine/platform/3ds/render/character_renderer.cpp engine/platform/3ds/render/material_state.cpp)
  target_include_directories(test_ctr_character_material PRIVATE tests/cpp/render_doubles tests/cpp engine/platform/3ds/render)
  target_link_libraries(test_ctr_character_material PRIVATE sh3_application sh3_diagnostics sh3_options)
  foreach(scenario IN ITEMS normal invalid busy flush draw init_MATERIAL init_PIXELS
      init_CITRO3D init_TARGET init_SHADER init_EMPTY_SHADER init_PROGRAM init_VERTEX_SHADER
      init_UNIFORM init_VERTICES init_ATTRIBUTES_0 init_ATTRIBUTES_1 init_ATTRIBUTES_2 init_BUFFER
      init_TEXTURE_0 init_TEXTURE_1 init_TEXTURE_2 init_TEXTURE_FLUSH_0 init_TEXTURE_FLUSH_1 init_TEXTURE_FLUSH_2)
    add_test(NAME character_material_gpu_${scenario} COMMAND test_ctr_character_material ${scenario})
    set_tests_properties(character_material_gpu_${scenario} PROPERTIES LABELS "integration;contract;sdk-double;render" TIMEOUT 15)
    add_test(NAME character_world_gpu_${scenario} COMMAND test_ctr_character_material ${scenario} 3)
    set_tests_properties(character_world_gpu_${scenario} PROPERTIES LABELS "integration;contract;sdk-double;render" TIMEOUT 15)
  endforeach()
  add_executable(test_animation_probe tests/cpp/test_animation_probe.cpp)
  target_include_directories(test_animation_probe PRIVATE tests/cpp)
  target_link_libraries(test_animation_probe PRIVATE sh3_application sh3_diagnostics sh3_options)
  add_test(NAME animation_probe COMMAND test_animation_probe)
  set_tests_properties(animation_probe PROPERTIES LABELS "unit;contract;render" TIMEOUT 10)
  add_executable(test_ctr_animation tests/cpp/test_ctr_animation.cpp tests/cpp/render_doubles/sdk.cpp
    engine/platform/3ds/render/renderer.cpp engine/platform/3ds/render/material_state.cpp)
  target_include_directories(test_ctr_animation PRIVATE tests/cpp/render_doubles
    tests/cpp engine/platform/3ds/render)
  target_link_libraries(test_ctr_animation PRIVATE sh3_application sh3_diagnostics sh3_options)
  foreach(scenario IN ITEMS normal invalid busy flush draw)
    add_test(NAME animation_gpu_${scenario} COMMAND test_ctr_animation ${scenario})
    set_tests_properties(animation_gpu_${scenario} PROPERTIES
      LABELS "integration;contract;sdk-double;render" TIMEOUT 10)
  endforeach()
  add_executable(test_inspection_texture tests/cpp/test_inspection_texture.cpp)
  target_include_directories(test_inspection_texture PRIVATE tests/cpp)
  target_link_libraries(test_inspection_texture PRIVATE sh3_diagnostics sh3_options)
  add_test(NAME inspection_texture COMMAND test_inspection_texture)
  set_tests_properties(inspection_texture PROPERTIES LABELS "unit;contract;render" TIMEOUT 10)
  add_executable(test_render_probe tests/cpp/test_render_probe.cpp)
  target_include_directories(test_render_probe PRIVATE tests/cpp)
  target_link_libraries(test_render_probe PRIVATE sh3_application sh3_diagnostics sh3_options)
  add_test(NAME render_probe COMMAND test_render_probe)
  set_tests_properties(render_probe PROPERTIES LABELS "unit;contract;render" TIMEOUT 10)
  add_executable(test_ctr_render tests/cpp/test_ctr_render.cpp tests/cpp/render_doubles/sdk.cpp
    engine/platform/3ds/render/renderer.cpp engine/platform/3ds/render/material_state.cpp)
  target_include_directories(test_ctr_render PRIVATE tests/cpp/render_doubles
    tests/cpp engine/platform/3ds/render)
  target_link_libraries(test_ctr_render PRIVATE sh3_application sh3_diagnostics sh3_options)
  foreach(scenario IN ITEMS normal CITRO3D TARGET SHADER EMPTY_SHADER PROGRAM VERTEX_SHADER
      UNIFORM VERTICES VERTEX_FLUSH TEXTURE TEXTURE_FLUSH ATTRIBUTES ATTRIBUTES_1 ATTRIBUTES_2
      BUFFER FRAME_BEGIN DRAW_ON invalid_camera)
    add_test(NAME render_${scenario} COMMAND test_ctr_render ${scenario})
    set_tests_properties(render_${scenario} PROPERTIES
      LABELS "integration;contract;sdk-double;render" TIMEOUT 10)
  endforeach()
  foreach(scenario IN ITEMS normal CITRO3D TARGET SHADER EMPTY_SHADER PROGRAM VERTEX_SHADER
      UNIFORM VERTICES VERTEX_FLUSH TEXTURE TEXTURE_FLUSH ATTRIBUTES ATTRIBUTES_1 ATTRIBUTES_2
      BUFFER FRAME_BEGIN DRAW_ON invalid_camera invalid_pixels)
    add_test(NAME texture_render_${scenario} COMMAND test_ctr_render ${scenario} texture)
    set_tests_properties(texture_render_${scenario} PROPERTIES
      LABELS "integration;contract;sdk-double;render" TIMEOUT 10)
  endforeach()
  foreach(scenario IN ITEMS normal CITRO3D TARGET SHADER EMPTY_SHADER PROGRAM VERTEX_SHADER
      UNIFORM VERTICES VERTEX_FLUSH TEXTURE TEXTURE_FLUSH ATTRIBUTES ATTRIBUTES_1 ATTRIBUTES_2
      BUFFER FRAME_BEGIN DRAW_ON invalid_camera invalid_mesh)
    add_test(NAME geometry_render_${scenario} COMMAND test_ctr_render ${scenario} geometry)
    set_tests_properties(geometry_render_${scenario} PROPERTIES
      LABELS "integration;contract;sdk-double;render" TIMEOUT 10)
  endforeach()
  foreach(scenario IN ITEMS normal CITRO3D TARGET SHADER EMPTY_SHADER PROGRAM VERTEX_SHADER
      UNIFORM VERTICES VERTEX_FLUSH TEXTURE TEXTURE_FLUSH ATTRIBUTES ATTRIBUTES_1 ATTRIBUTES_2
      BUFFER FRAME_BEGIN DRAW_ON invalid_camera invalid_mesh invalid_pixels)
    add_test(NAME material_render_${scenario} COMMAND test_ctr_render ${scenario} material)
    set_tests_properties(material_render_${scenario} PROPERTIES
      LABELS "integration;contract;sdk-double;render" TIMEOUT 10)
  endforeach()
  add_executable(test_inspection_geometry tests/cpp/test_inspection_geometry.cpp)
  target_include_directories(test_inspection_geometry PRIVATE tests/cpp)
  target_link_libraries(test_inspection_geometry PRIVATE sh3_diagnostics sh3_options)
  add_test(NAME inspection_geometry COMMAND test_inspection_geometry)
  set_tests_properties(inspection_geometry PROPERTIES LABELS "unit;contract;render" TIMEOUT 10)
  # Host-only observer domain. Nintendo targets never depend on the PCSX2 tooling.
  find_package(Threads REQUIRED)
  find_package(Python3 REQUIRED COMPONENTS Interpreter)
  add_test(NAME character_material_wire COMMAND ${Python3_EXECUTABLE}
    ${CMAKE_CURRENT_SOURCE_DIR}/tests/character_material_wire_oracle.py $<TARGET_FILE:test_character_material>)
  add_test(NAME character_lighting_wire COMMAND ${Python3_EXECUTABLE}
    ${CMAKE_CURRENT_SOURCE_DIR}/tests/character_lighting_wire_oracle.py $<TARGET_FILE:test_character_lighting>)
  add_test(NAME character_world_wire COMMAND ${Python3_EXECUTABLE}
    ${CMAKE_CURRENT_SOURCE_DIR}/tests/character_world_wire_oracle.py $<TARGET_FILE:test_character_world>)
  set_tests_properties(character_world_wire PROPERTIES LABELS "integration;contract;render" TIMEOUT 30)
  set_tests_properties(character_lighting_wire PROPERTIES LABELS "integration;contract;render" TIMEOUT 30)
  set_tests_properties(character_material_wire PROPERTIES LABELS "integration;contract;render" TIMEOUT 30)
  add_test(NAME character_wire_oracle COMMAND ${Python3_EXECUTABLE}
    ${CMAKE_CURRENT_SOURCE_DIR}/tests/character_wire_oracle.py $<TARGET_FILE:test_character_skinning>)
  set_tests_properties(character_wire_oracle PROPERTIES LABELS "integration;contract;render" TIMEOUT 30)
  add_test(NAME animation_wire_oracle COMMAND ${Python3_EXECUTABLE}
    ${CMAKE_CURRENT_SOURCE_DIR}/tests/animation_wire_oracle.py $<TARGET_FILE:test_animation_probe>)
  set_tests_properties(animation_wire_oracle PROPERTIES LABELS "integration;contract;render" TIMEOUT 30)
  add_test(NAME inspection_texture_wire COMMAND ${Python3_EXECUTABLE}
    ${CMAKE_CURRENT_SOURCE_DIR}/tests/texture_wire_oracle.py $<TARGET_FILE:test_inspection_texture>)
  set_tests_properties(inspection_texture_wire PROPERTIES LABELS "integration;contract;render" TIMEOUT 10)
  add_test(NAME inspection_geometry_wire COMMAND ${Python3_EXECUTABLE}
    ${CMAKE_CURRENT_SOURCE_DIR}/tests/geometry_wire_oracle.py $<TARGET_FILE:test_inspection_geometry>)
  set_tests_properties(inspection_geometry_wire PROPERTIES LABELS "integration;contract;render" TIMEOUT 10)
  add_library(sh3_observer tools/observer/capture.cpp tools/observer/wire.cpp)
  target_include_directories(sh3_observer PUBLIC tools/observer/include)
  target_link_libraries(sh3_observer PRIVATE sh3_options)
  add_executable(test_observer tests/cpp/test_observer.cpp)
  target_include_directories(test_observer PRIVATE tests/cpp)
  target_link_libraries(test_observer PRIVATE sh3_observer sh3_options Threads::Threads)
  add_test(NAME observer COMMAND test_observer)
  add_test(NAME observer_wire_oracle COMMAND ${Python3_EXECUTABLE}
    ${CMAKE_CURRENT_SOURCE_DIR}/tests/observer_wire_oracle.py $<TARGET_FILE:test_observer>)
  set_tests_properties(observer observer_wire_oracle PROPERTIES
    LABELS "unit;contract;observer" TIMEOUT 15)
  add_library(sh3_lifetime tools/observer/lifetime.cpp)
  target_include_directories(sh3_lifetime PUBLIC tools/observer/include)
  target_link_libraries(sh3_lifetime PRIVATE sh3_options)
  add_executable(test_lifetime tests/cpp/test_lifetime.cpp)
  target_include_directories(test_lifetime PRIVATE tests/cpp)
  target_link_libraries(test_lifetime PRIVATE sh3_lifetime sh3_options)
  foreach(scenario IN ITEMS valid plan identity sequence cycles budget writes lifecycle protocol terminal boundaries)
    add_test(NAME lifetime_${scenario} COMMAND test_lifetime ${scenario})
    set_tests_properties(lifetime_${scenario} PROPERTIES LABELS "unit;contract;lifetime" TIMEOUT 15)
  endforeach()
  add_library(sh3_physical_writes tools/observer/physical_writes.cpp tools/observer/host_epoch.cpp)
  target_include_directories(sh3_physical_writes PUBLIC tools/observer/include)
  target_link_libraries(sh3_physical_writes PUBLIC sh3_lifetime PRIVATE sh3_options Threads::Threads)
  add_executable(test_physical_writes tests/cpp/test_physical_writes.cpp)
  target_include_directories(test_physical_writes PRIVATE tests/cpp)
  target_link_libraries(test_physical_writes PRIVATE sh3_physical_writes sh3_options Threads::Threads)
  foreach(scenario IN ITEMS valid boundaries protected unknown binding concurrent terminal)
    add_test(NAME physical_writes_${scenario} COMMAND test_physical_writes ${scenario})
    set_tests_properties(physical_writes_${scenario} PROPERTIES LABELS "unit;contract;lifetime" TIMEOUT 15)
  endforeach()
  add_executable(test_host_lifecycle tests/cpp/test_host_lifecycle.cpp)
  target_include_directories(test_host_lifecycle PRIVATE tests/cpp)
  target_link_libraries(test_host_lifecycle PRIVATE sh3_physical_writes sh3_options Threads::Threads)
  foreach(scenario IN ITEMS epoch exhaustion concurrent_epoch causes invalid_kind binding terminal concurrent_notices)
    add_test(NAME host_lifecycle_${scenario} COMMAND test_host_lifecycle ${scenario})
    set_tests_properties(host_lifecycle_${scenario} PROPERTIES LABELS "unit;contract;lifetime" TIMEOUT 15)
  endforeach()
  add_library(sh3_admission tools/observer/admission.cpp)
  target_include_directories(sh3_admission PUBLIC tools/observer/include)
  target_link_libraries(sh3_admission PRIVATE sh3_options)
  add_executable(test_admission tests/cpp/test_admission.cpp)
  target_include_directories(test_admission PRIVATE tests/cpp)
  target_link_libraries(test_admission PRIVATE sh3_admission sh3_options Threads::Threads)
  foreach(scenario IN ITEMS defaults single combinations invalid independent concurrent)
    add_test(NAME admission_${scenario} COMMAND test_admission ${scenario})
    set_tests_properties(admission_${scenario} PROPERTIES LABELS "unit;contract;admission" TIMEOUT 15)
  endforeach()
  add_library(sh3_cpu_boundary tools/observer/cpu_boundary.cpp)
  target_include_directories(sh3_cpu_boundary PUBLIC tools/observer/include)
  target_link_libraries(sh3_cpu_boundary PRIVATE sh3_options)
  add_executable(test_cpu_boundary tests/cpp/test_cpu_boundary.cpp)
  target_include_directories(test_cpu_boundary PRIVATE tests/cpp)
  target_link_libraries(test_cpu_boundary PRIVATE sh3_cpu_boundary sh3_options Threads::Threads)
  foreach(scenario IN ITEMS offline online activity revoked nested_activity reentry restart unwind threads)
    add_test(NAME cpu_boundary_${scenario} COMMAND test_cpu_boundary ${scenario})
    set_tests_properties(cpu_boundary_${scenario} PROPERTIES LABELS "unit;contract;exclusion" TIMEOUT 15)
  endforeach()
  add_library(sh3_cooperative_gate tools/observer/cooperative_gate.cpp)
  target_include_directories(sh3_cooperative_gate PUBLIC tools/observer/include)
  target_link_libraries(sh3_cooperative_gate PRIVATE sh3_options Threads::Threads)
  add_library(sh3_pine_drain tools/observer/pine_drain.cpp)
  target_include_directories(sh3_pine_drain PUBLIC tools/observer/include)
  target_link_libraries(sh3_pine_drain PUBLIC sh3_cooperative_gate sh3_cpu_boundary PRIVATE sh3_options)
  add_executable(test_pine_drain tests/cpp/test_pine_drain.cpp)
  target_include_directories(test_pine_drain PRIVATE tests/cpp)
  target_link_libraries(test_pine_drain PRIVATE sh3_pine_drain sh3_options Threads::Threads)
  foreach(scenario IN ITEMS submit complete draining discarded cancel timeout identity boundary contention shutdown)
    add_test(NAME pine_drain_${scenario} COMMAND test_pine_drain ${scenario})
    set_tests_properties(pine_drain_${scenario} PROPERTIES LABELS "unit;contract;exclusion" TIMEOUT 15)
  endforeach()
  add_executable(test_cooperative_gate tests/cpp/test_cooperative_gate.cpp)
  add_library(sh3_retained_drain tools/observer/retained_drain.cpp)
  target_include_directories(sh3_retained_drain PUBLIC tools/observer/include)
  target_link_libraries(sh3_retained_drain PUBLIC sh3_pine_drain PRIVATE sh3_options)
  add_executable(test_retained_drain tests/cpp/test_retained_drain.cpp)
  target_include_directories(test_retained_drain PRIVATE tests/cpp)
  target_link_libraries(test_retained_drain PRIVATE sh3_retained_drain sh3_options Threads::Threads)
  foreach(scenario IN ITEMS submit phases complete cancel rejection invalidation timeout reentry release_order shutdown)
    add_test(NAME retained_drain_${scenario} COMMAND test_retained_drain ${scenario})
    set_tests_properties(retained_drain_${scenario} PROPERTIES LABELS "unit;contract;exclusion" TIMEOUT 15)
  endforeach()
  target_include_directories(test_cooperative_gate PRIVATE tests/cpp)
  target_link_libraries(test_cooperative_gate PRIVATE sh3_cooperative_gate sh3_options Threads::Threads)
  foreach(scenario IN ITEMS open shared draining contention deadline cancellation capacity unwind concurrent)
    add_test(NAME cooperative_gate_${scenario} COMMAND test_cooperative_gate ${scenario})
    set_tests_properties(cooperative_gate_${scenario} PROPERTIES LABELS "unit;contract;exclusion" TIMEOUT 15)
  endforeach()
  add_executable(test_cooperative_gate_allocation tests/cpp/test_cooperative_gate_allocation.cpp)
  target_include_directories(test_cooperative_gate_allocation PRIVATE tests/cpp)
  target_link_libraries(test_cooperative_gate_allocation PRIVATE sh3_cooperative_gate sh3_options Threads::Threads)
  add_test(NAME cooperative_gate_allocation COMMAND test_cooperative_gate_allocation)
  set_tests_properties(cooperative_gate_allocation PROPERTIES LABELS "unit;contract;exclusion" TIMEOUT 15)
  add_library(sh3_worker_control tools/observer/worker_control.cpp)
  target_include_directories(sh3_worker_control PUBLIC tools/observer/include)
  target_compile_features(sh3_worker_control PUBLIC cxx_std_20)
  target_link_libraries(sh3_worker_control PRIVATE sh3_options Threads::Threads)
  add_library(sh3_worker_drain tools/observer/worker_drain.cpp)
  target_include_directories(sh3_worker_drain PUBLIC tools/observer/include)
  target_link_libraries(sh3_worker_drain PUBLIC sh3_worker_control sh3_retained_drain PRIVATE sh3_options)
  add_library(sh3_external_waits tools/observer/external_waits.cpp)
  target_include_directories(sh3_external_waits PUBLIC tools/observer/include)
  target_link_libraries(sh3_external_waits PRIVATE sh3_options Threads::Threads)
  add_executable(test_external_waits tests/cpp/test_external_waits.cpp)
  target_include_directories(test_external_waits PRIVATE tests/cpp)
  target_link_libraries(test_external_waits PRIVATE sh3_external_waits sh3_options Threads::Threads)
  foreach(scenario IN ITEMS scope nested capacity concurrent publication unwind)
    add_test(NAME external_waits_${scenario} COMMAND test_external_waits ${scenario})
    set_tests_properties(external_waits_${scenario} PROPERTIES LABELS "unit;contract;exclusion" TIMEOUT 15)
  endforeach()
  add_executable(test_worker_drain tests/cpp/test_worker_drain.cpp)
  target_include_directories(test_worker_drain PRIVATE tests/cpp)
  target_link_libraries(test_worker_drain PRIVATE sh3_worker_drain sh3_options Threads::Threads)
  foreach(scenario IN ITEMS sequence cancel rejection offline generations lost_token epochs timeout
      tickets exhaustion restart revalidation conflict acknowledgement_race dependency invalid_request)
    add_test(NAME worker_drain_${scenario} COMMAND test_worker_drain ${scenario})
    set_tests_properties(worker_drain_${scenario} PROPERTIES LABELS "unit;contract;exclusion" TIMEOUT 15)
  endforeach()
  add_executable(test_worker_control tests/cpp/test_worker_control.cpp)
  target_include_directories(test_worker_control PRIVATE tests/cpp)
  target_link_libraries(test_worker_control PRIVATE sh3_worker_control sh3_options Threads::Threads)
  foreach(scenario IN ITEMS defaults identity cancel lifecycle retained_stop exhaustion
      wake_coalescing wake_between_check_and_wait wake_publication multiple_notifiers coalesced_publication
      shared_owner ack_publication release_ack_race request_stop_race stop_release_race full_data_queue)
    add_test(NAME worker_control_${scenario} COMMAND test_worker_control ${scenario})
    set_tests_properties(worker_control_${scenario} PROPERTIES LABELS "unit;contract;exclusion" TIMEOUT 15)
  endforeach()
  add_executable(test_worker_control_allocation tests/cpp/test_worker_control_allocation.cpp)
  target_include_directories(test_worker_control_allocation PRIVATE tests/cpp)
  target_link_libraries(test_worker_control_allocation PRIVATE sh3_worker_control sh3_options Threads::Threads)
  add_test(NAME worker_control_allocation COMMAND test_worker_control_allocation)
  set_tests_properties(worker_control_allocation PROPERTIES LABELS "unit;contract;exclusion" TIMEOUT 15)
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
