#include "fixture.hpp"
#include <QBuffer>
#include <QGuiApplication>
#include <QImage>
#include <QImageReader>
#include <QImageWriter>
#include <cmath>

static QImage roundtrip(const QImage& input, const char* format, int quality) {
    QByteArray encoded;
    QBuffer output(&encoded);
    require(output.open(QIODevice::WriteOnly), "buffer open failed");
    QImageWriter writer(&output, format);
    writer.setQuality(quality);
    require(writer.write(input), "image encoding failed");
    output.close();
    QImage decoded;
    require(decoded.loadFromData(encoded, format), "image decoding failed");
    require(decoded.size() == input.size(), "image dimensions changed");
    return decoded;
}

static void pngCase() {
    require(QImageReader::supportedImageFormats().contains("png"), "PNG reader absent");
    QImage input(8, 8, QImage::Format_ARGB32);
    for (int y = 0; y < input.height(); ++y)
        for (int x = 0; x < input.width(); ++x)
            input.setPixelColor(x, y, QColor(x * 31, y * 29, 113, 64 + x * 20));
    const auto decoded = roundtrip(input, "PNG", 100);
    for (int y = 0; y < input.height(); ++y)
        for (int x = 0; x < input.width(); ++x)
            require(decoded.pixelColor(x, y) == input.pixelColor(x, y), "PNG pixel mismatch");
    QImage invalid;
    require(!invalid.loadFromData(QByteArray("\x89PNG\r\n\x1a\ninvalid"), "PNG"), "corrupt PNG accepted");
}

static void jpegCase() {
    require(QImageReader::supportedImageFormats().contains("jpeg"), "JPEG reader absent");
    QImage input(8, 8, QImage::Format_RGB32);
    const QColor color(32, 96, 160);
    input.fill(color);
    const auto decoded = roundtrip(input, "JPEG", 95);
    for (int y = 0; y < decoded.height(); ++y)
        for (int x = 0; x < decoded.width(); ++x) {
            const auto actual = decoded.pixelColor(x, y);
            require(std::abs(actual.red() - color.red()) <= 12
                && std::abs(actual.green() - color.green()) <= 12
                && std::abs(actual.blue() - color.blue()) <= 12, "JPEG color exceeds tolerance");
        }
    QImage invalid;
    require(!invalid.loadFromData(QByteArray("invalid JPEG"), "JPEG"), "corrupt JPEG accepted");
}

int main(int argc, char** argv) {
    QGuiApplication app(argc, argv);
    return checked([&] {
        require(argc == 2, "expected one case name");
        require(app.platformName() == "offscreen", "unexpected platform");
        const std::string_view name(argv[1]);
        if (name == "png") pngCase();
        else if (name == "jpeg") jpegCase();
        else throw std::runtime_error("unknown case");
    });
}
