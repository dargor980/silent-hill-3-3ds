#pragma once
#include <iostream>
#include <stdexcept>
inline void require(bool value, const char* message) {
    if (!value) throw std::runtime_error(message);
}
template<class Function> int checked(Function action) {
    try { action(); std::cout << "PASS\n"; return 0; }
    catch (const std::exception& error) { std::cerr << error.what() << '\n'; return 1; }
}
