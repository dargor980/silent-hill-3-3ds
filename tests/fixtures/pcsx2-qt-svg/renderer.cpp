#include "fixture.hpp"
#include <QGuiApplication>
#include <QPainter>
#include <QSvgRenderer>

static QImage render(QSvgRenderer& renderer) {
    QImage result(32, 24, QImage::Format_ARGB32_Premultiplied);
    result.fill(Qt::transparent);
    QPainter painter(&result);
    renderer.render(&painter);
    painter.end();
    return result;
}

int main(int argc, char** argv) {
    QGuiApplication application(argc, argv);
    return checked([&] {
        require(argc == 4, "Expected case, valid SVG, invalid SVG");
        const QString mode = QString::fromLocal8Bit(argv[1]);
        QSvgRenderer renderer;
        if (mode == "invalid") {
            require(!renderer.load(QString::fromLocal8Bit(argv[3])), "Invalid XML was accepted");
            require(!renderer.isValid(), "Invalid renderer marked valid");
        } else require(mode == "basics" || mode == "transformed", "Unknown case");
        require(renderer.load(QString::fromLocal8Bit(argv[2])), "Could not load own SVG");
        require(renderer.isValid(), "Valid SVG rejected");
        require(renderer.defaultSize() == QSize(32, 24), "Wrong default size");
        require(renderer.viewBoxF() == QRectF(0, 0, 32, 24), "Wrong view box");
        const auto result = render(renderer);
        basics(result);
        if (mode == "transformed" || mode == "invalid") transformed(result);
    });
}
