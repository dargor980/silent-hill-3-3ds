#include <QDir>
#include <QEventLoop>
#include <QFile>
#include <QGuiApplication>
#include <QImageReader>
#include <QJsonArray>
#include <QJsonDocument>
#include <QJsonObject>
#include <QMovie>
#include <QTimer>
#include <iostream>
#include <stdexcept>

namespace {
void require(bool ok, const QString& reason) {
    if (!ok) throw std::runtime_error(reason.toStdString());
}

void compare(const QImage& image, const QJsonObject& spec, int index) {
    require(!image.isNull(), "Null image");
    const int width = spec["width"].toInt(), height = spec["height"].toInt();
    require(image.size() == QSize(width, height), "Wrong image dimensions");
    const auto pixels = spec["images"].toArray().at(index).toArray();
    require(pixels.size() == width * height, "Invalid pixel oracle");
    for (int y = 0; y < height; ++y) {
        for (int x = 0; x < width; ++x) {
            const auto expected = pixels.at(y * width + x).toArray();
            const QColor wanted(expected.at(0).toInt(), expected.at(1).toInt(), expected.at(2).toInt(), expected.at(3).toInt());
            require(image.pixelColor(x, y) == wanted, "RGBA mismatch at frame " + QString::number(index) +
                    " pixel " + QString::number(y * width + x));
        }
    }
}

void readAll(const QString& filename, const QJsonObject& spec) {
    require(!spec.isEmpty(), "Missing oracle");
    QImageReader reader(filename, "apng");
    reader.setAutoDetectImageFormat(false);
    require(reader.canRead(), "Cannot read fixture");
    require(reader.size() == QSize(spec["width"].toInt(), spec["height"].toInt()), "Wrong metadata dimensions");
    require(reader.supportsAnimation() == spec["animated"].toBool(), "Wrong animation flag");
    const int frames = spec["images"].toArray().size();
    require(reader.imageCount() == frames, "Wrong frame count: " + QString::number(reader.imageCount()));
    require(reader.loopCount() == spec["loops"].toInt(), "Wrong loop count: expected " +
            QString::number(spec["loops"].toInt()) + ", got " + QString::number(reader.loopCount()));
    for (int index = 0; index < frames; ++index) {
        compare(reader.read(), spec, index);
        const int delay = reader.nextImageDelay();
        require(delay == spec["delays"].toArray().at(index).toInt(), "Wrong frame delay: " + QString::number(delay));
    }
    require(reader.read().isNull(), "Unexpected extra frame");
    if (spec["animated"].toBool()) {
        require(reader.jumpToImage(0), "Cannot rewind cached frames");
        compare(reader.read(), spec, 0);
    }
}

void play(const QString& filename, const QJsonObject& spec) {
    QMovie movie(filename, "apng");
    movie.setCacheMode(QMovie::CacheAll);
    require(movie.isValid(), "QMovie rejected valid fixture");
    QEventLoop loop;
    QTimer timer;
    timer.setSingleShot(true);
    QList<int> seen;
    QString failure;
    bool finished = false, timedOut = false;
    QObject::connect(&movie, &QMovie::frameChanged, &loop, [&](int index) {
        try {
            require(index == seen.size() % spec["images"].toArray().size(), "QMovie frame order mismatch");
            compare(movie.currentImage(), spec, index);
            seen.append(index);
        } catch (const std::exception& error) {
            failure = QString::fromUtf8(error.what());
            loop.quit();
        }
    });
    QObject::connect(&movie, &QMovie::finished, &loop, [&] { finished = true; loop.quit(); });
    QObject::connect(&movie, &QMovie::error, &loop, [&](QImageReader::ImageReaderError) {
        failure = movie.lastErrorString(); loop.quit();
    });
    QObject::connect(&timer, &QTimer::timeout, &loop, [&] { timedOut = true; loop.quit(); });
    timer.start(5000);
    movie.start();
    if (!finished && failure.isEmpty()) loop.exec();
    movie.stop();
    require(!timedOut && failure.isEmpty() && finished, "QMovie completion failed: " + failure);
    const int wanted = spec["plays"].toInt() * spec["images"].toArray().size();
    require(seen.size() == wanted, "QMovie extra/missing frames: expected " + QString::number(wanted) +
            ", got " + QString::number(seen.size()));
    std::cout << "movie frames=" << seen.size() << '\n';
}
}

int main(int argc, char** argv) {
    QGuiApplication app(argc, argv);
    try {
        require(argc == 4, "Expected case, data directory and plugin root");
        const QString mode = QString::fromLocal8Bit(argv[1]);
        const QDir data(QString::fromLocal8Bit(argv[2]));
        QCoreApplication::setLibraryPaths({QString::fromLocal8Bit(argv[3])});
        QFile input(data.filePath("oracle.json"));
        require(input.open(QIODevice::ReadOnly), "Cannot read oracle");
        QJsonParseError error;
        const auto document = QJsonDocument::fromJson(input.readAll(), &error);
        require(error.error == QJsonParseError::NoError && document.isObject(), "Invalid oracle");
        const auto oracle = document.object();
        if (mode == "isolation") {
            require(!QImageReader::supportedImageFormats().contains("apng"), "APNG leaked from other plugin root");
            QImageReader reader(data.filePath("plays-1.apng"), "apng");
            reader.setAutoDetectImageFormat(false);
            require(!reader.canRead() && reader.read().isNull(), "APNG accepted without plugin");
        } else {
            require(QImageReader::supportedImageFormats().contains("apng") && QMovie::supportedFormats().contains("apng"),
                    "APNG plugin unavailable");
            const auto read = [&](const QString& name) { readAll(data.filePath(name), oracle[name].toObject()); };
            if (mode == "composition") read("composition.apng");
            else if (mode == "finite") { read("plays-1.apng"); read("plays-2.apng"); }
            else if (mode == "timing") read("zero-den.apng");
            else if (mode == "hidden") read("hidden.apng");
            else if (mode == "static") read("static.png");
            else if (mode == "invalid") {
                for (const auto& name : {"invalid.apng", "truncated.apng", "empty.apng", "short.apng"}) {
                    QImageReader reader(data.filePath(name), "apng");
                    reader.setAutoDetectImageFormat(false);
                    require(reader.read().isNull(), "Invalid APNG accepted");
                    require(reader.error() != QImageReader::UnknownError && !reader.errorString().isEmpty(), "Missing error diagnostic");
                    reader.setFileName(data.filePath("composition.apng"));
                    reader.setFormat("apng");
                    compare(reader.read(), oracle["composition.apng"].toObject(), 0);
                }
            } else if (mode == "movie") {
                for (const auto& name : {"plays-1.apng", "plays-2.apng"}) play(data.filePath(name), oracle[name].toObject());
            } else throw std::runtime_error("Unknown case");
        }
        std::cout << mode.toStdString() << " passed\n";
        return 0;
    } catch (const std::exception& error) {
        std::cerr << error.what() << '\n';
        return 1;
    }
}
