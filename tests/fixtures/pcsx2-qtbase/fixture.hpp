#pragma once
#include <iostream>
#include <stdexcept>
#include <string_view>

inline void require(bool condition, const char* message) {
    if (!condition) throw std::runtime_error(message);
}
template<class Function> int checked(Function function) {
    try { function(); return 0; }
    catch (const std::exception& error) {
        std::cerr << error.what() << '\n';
        return 1;
    }
}
