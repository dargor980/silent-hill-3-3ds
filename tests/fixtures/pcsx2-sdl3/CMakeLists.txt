cmake_minimum_required(VERSION 3.25)
project(sh3_sdl3_fixture LANGUAGES CXX)

if(NOT SH3_SDL_CONFIG_DIR)
    message(FATAL_ERROR "Set SH3_SDL_CONFIG_DIR to the private SDL3Config.cmake directory")
endif()
if(NOT EXISTS "${SH3_SDL_CONFIG_DIR}/SDL3Config.cmake")
    message(FATAL_ERROR "SDL3Config.cmake is missing from the explicit directory")
endif()
set(SDL3_DIR "${SH3_SDL_CONFIG_DIR}")
find_package(SDL3 3.4.12 EXACT CONFIG REQUIRED
    PATHS "${SH3_SDL_CONFIG_DIR}" NO_DEFAULT_PATH)

add_executable(sh3_sdl3_fixture main.cpp)
target_compile_features(sh3_sdl3_fixture PRIVATE cxx_std_20)
target_compile_options(sh3_sdl3_fixture PRIVATE -Wall -Wextra -Werror)
target_link_libraries(sh3_sdl3_fixture PRIVATE SDL3::SDL3-shared)

enable_testing()
foreach(case IN ITEMS events gamepad audio memory)
    add_test(NAME sdl3-${case} COMMAND sh3_sdl3_fixture ${case})
    set_tests_properties(sdl3-${case} PROPERTIES
        TIMEOUT 15
        ENVIRONMENT "SDL_AUDIO_DRIVER=dummy;SDL_JOYSTICK_HIDAPI=0;SDL_JOYSTICK_IOKIT=0;SDL_JOYSTICK_MFI=0;SDL_JOYSTICK_ALLOW_BACKGROUND_EVENTS=1")
endforeach()
