#pragma once
#include <QColor>
#include <QImage>
#include <cmath>
#include <iostream>
#include <stdexcept>

inline void require(bool condition, const char* message) {
    if (!condition) throw std::runtime_error(message);
}

inline void pixel(const QImage& image, int x, int y, QColor expected, int tolerance = 0) {
    require(image.valid(x, y), "Pixel outside image");
    const QColor actual = image.pixelColor(x, y);
    if (std::abs(actual.red() - expected.red()) > tolerance ||
        std::abs(actual.green() - expected.green()) > tolerance ||
        std::abs(actual.blue() - expected.blue()) > tolerance ||
        std::abs(actual.alpha() - expected.alpha()) > tolerance) {
        std::cerr << "Pixel (" << x << ',' << y << ") actual RGBA "
                  << actual.red() << ',' << actual.green() << ','
                  << actual.blue() << ',' << actual.alpha() << '\n';
        throw std::runtime_error("Unexpected pixel");
    }
}

inline void basics(const QImage& image, int scale = 1) {
    require(image.size() == QSize(32 * scale, 24 * scale), "Unexpected image dimensions");
    pixel(image, 8 * scale, 8 * scale, QColor(224, 32, 48));
    pixel(image, scale, scale, QColor(0, 0, 0, 0));
    pixel(image, 30 * scale, 22 * scale, QColor(0, 0, 0, 0));
}

inline void transformed(const QImage& image, int scale = 1) {
    // Only interior pixels. One level allows premultiplied-alpha rounding.
    pixel(image, 20 * scale, 12 * scale, QColor(32, 64, 224, 128), 1);
    pixel(image, 6 * scale, 18 * scale, QColor(16, 160, 48));
}

template<class Function> int checked(Function action) {
    try { action(); std::cout << "PASS\n"; return 0; }
    catch (const std::exception& error) { std::cerr << error.what() << '\n'; return 1; }
}
