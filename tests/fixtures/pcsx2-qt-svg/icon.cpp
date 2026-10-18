#include "fixture.hpp"
#include <QGuiApplication>
#include <QIcon>

int main(int argc, char** argv) {
    QGuiApplication application(argc, argv);
    return checked([] {
        const QIcon icon(QStringLiteral(":/qs/scene.svg"));
        require(!icon.isNull(), "SVG resource icon is null");
        const auto pixmap = icon.pixmap(QSize(64, 48), 1.0);
        require(!pixmap.isNull(), "SVG icon pixmap is null");
        require(pixmap.devicePixelRatio() == 1.0, "Wrong explicit pixel ratio");
        const auto image = pixmap.toImage();
        basics(image, 2); transformed(image, 2);
    });
}
