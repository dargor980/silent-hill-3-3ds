#pragma once

#include <cstdio>
#include <cstdlib>

// Unlike assert(), these checks are still active in Release/NDEBUG builds.
#define CHECK(expression)                                                                          \
    do {                                                                                           \
        if (!(expression)) {                                                                       \
            std::fprintf(stderr, "%s:%d check failed: %s\n", __FILE__, __LINE__, #expression);     \
            std::exit(EXIT_FAILURE);                                                               \
        }                                                                                          \
    } while (false)
