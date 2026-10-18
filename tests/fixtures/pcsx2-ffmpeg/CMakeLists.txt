cmake_minimum_required(VERSION 3.25)
project(sh3_ffmpeg_fixture LANGUAGES C CXX)
enable_testing()
if(NOT EXISTS "${SH3_FFMPEG_HEADERS}/libavcodec/avcodec.h" OR
   NOT EXISTS "${SH3_FFMPEG_GENERATED}/libavutil/avconfig.h" OR
   NOT IS_DIRECTORY "${SH3_FFMPEG_LIBROOT}")
  message(FATAL_ERROR "Set explicit SH3_FFMPEG_HEADERS, SH3_FFMPEG_GENERATED and SH3_FFMPEG_LIBROOT")
endif()
file(MAKE_DIRECTORY "${CMAKE_CURRENT_BINARY_DIR}/ffmpeg-headers")
foreach(component avutil swresample swscale avcodec avformat)
  # A source tree contains a text file named "version", which would shadow
  # the standard C++ <version> header. Expose only the library directories.
  file(CREATE_LINK "${SH3_FFMPEG_HEADERS}/lib${component}"
    "${CMAKE_CURRENT_BINARY_DIR}/ffmpeg-headers/lib${component}" SYMBOLIC RESULT linked)
  if(NOT linked STREQUAL "0")
    message(FATAL_ERROR "Cannot create isolated header view: ${linked}")
  endif()
  find_library(FM_${component} NAMES ${component}
    PATHS "${SH3_FFMPEG_LIBROOT}" "${SH3_FFMPEG_LIBROOT}/lib${component}"
    NO_DEFAULT_PATH REQUIRED)
  add_library(FM::${component} SHARED IMPORTED)
  set_target_properties(FM::${component} PROPERTIES
    IMPORTED_LOCATION "${FM_${component}}"
    INTERFACE_INCLUDE_DIRECTORIES "${SH3_FFMPEG_GENERATED};${CMAKE_CURRENT_BINARY_DIR}/ffmpeg-headers")
endforeach()
set(CMAKE_CXX_STANDARD 20)
set(CMAKE_CXX_STANDARD_REQUIRED ON)
set(CMAKE_CXX_EXTENSIONS OFF)
add_executable(fm_consumer consumer.cpp fixture.hpp)
target_link_libraries(fm_consumer PRIVATE FM::avformat FM::avcodec FM::swscale FM::swresample FM::avutil)
target_compile_options(fm_consumer PRIVATE -Wall -Wextra -Werror)
foreach(case profile pcm video wav scale resample errors)
  add_test(NAME fm_${case} COMMAND fm_consumer ${case} "${CMAKE_CURRENT_BINARY_DIR}")
  set_tests_properties(fm_${case} PROPERTIES TIMEOUT 30)
endforeach()
if(SH3_PROVIDER_SOURCE)
  if(NOT EXISTS "${SH3_PYTHON}")
    message(FATAL_ERROR "Set SH3_PYTHON for provider output comparison")
  endif()
  foreach(case md5 crc sha channel_layout)
    set(source "${SH3_PROVIDER_SOURCE}/libavutil/tests/${case}.c")
    set(reference "${SH3_PROVIDER_SOURCE}/tests/ref/fate/${case}")
    if(NOT EXISTS "${source}" OR NOT EXISTS "${reference}")
      message(FATAL_ERROR "Missing original test or FATE reference: ${case}")
    endif()
    add_executable(provider_${case} "${source}")
    target_link_libraries(provider_${case} PRIVATE FM::avutil)
    add_test(NAME provider_${case} COMMAND "${SH3_PYTHON}"
      "${CMAKE_CURRENT_SOURCE_DIR}/compare_provider.py"
      "$<TARGET_FILE:provider_${case}>" "${reference}")
    set_tests_properties(provider_${case} PROPERTIES TIMEOUT 30)
  endforeach()
endif()
