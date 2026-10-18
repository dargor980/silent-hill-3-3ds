#include "fixture.hpp"
#include <QGuiApplication>
#include <QImageReader>

int main(int argc, char** argv) {
    QGuiApplication application(argc, argv);
    return checked([&] {
        require(argc == 3, "Expected valid SVG and invalid SVG");
        const QString valid = QString::fromLocal8Bit(argv[1]);
        QImageReader reader(valid);
        require(reader.canRead(), "SVG plugin cannot read valid input");
        require(reader.format() == "svg", "Unexpected image format");
        require(reader.size() == QSize(32, 24), "Wrong SVG dimensions");
        const auto image = reader.read();
        basics(image); transformed(image);
        QImageReader scaled(valid);
        scaled.setScaledSize(QSize(64, 48));
        const auto large = scaled.read();
        basics(large, 2); transformed(large, 2);
        QImageReader recovery(QString::fromLocal8Bit(argv[2]));
        require(recovery.read().isNull(), "Invalid SVG image accepted");
        require(recovery.error() != QImageReader::UnknownError, "Missing reader error");
        recovery.setFileName(valid);
        const auto recovered = recovery.read();
        basics(recovered); transformed(recovered);
    });
}
