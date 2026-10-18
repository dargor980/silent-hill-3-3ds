// Plugin consumer: links only Qt Gui, never WebP or a format plugin directly.
#include "pattern.hpp"
#include <QGuiApplication>
#include <QImageReader>
#include <QImageWriter>
#include <QString>
#include <cmath>

static void pixel(const QImage& image, int x, int y, Pixel target, int tolerance = 0) {
    require(image.valid(x,y), "Pixel outside decoded image");
    const auto c = image.pixelColor(x,y);
    const std::array<int,4> actual{c.red(),c.green(),c.blue(),c.alpha()};
    for (std::size_t i=0; i<4; ++i) if (std::abs(actual[i]-target[i])>tolerance) {
        std::cerr << "Pixel " << x << ',' << y << " channel " << i << " actual " << actual[i]
                  << " expected " << int(target[i]) << '\n';
        throw std::runtime_error("Decoded pixel mismatch");
    }
}
static void allPixels(const QImage& image) {
    require(image.size() == QSize(width,height), "Wrong decoded dimensions");
    for (int y=0;y<height;++y) for (int x=0;x<width;++x) pixel(image,x,y,expected(x,y));
}
static QImage read(const QString& path, const QByteArray& format) {
    QImageReader reader(path);
    require(reader.canRead(), "Plugin cannot read fixture");
    require(reader.format() == format, "Wrong detected format");
    const auto image=reader.read(); require(!image.isNull(), "Decoder returned null"); return image;
}
static void wbmp(const QImage& image) {
    require(image.size() == QSize(9,3), "Wrong WBMP dimensions");
    for (int y=0;y<3;++y) for (int x=0;x<9;++x) {
        const auto c=static_cast<std::uint8_t>((x+y)%2 ? 255 : 0);
        pixel(image,x,y,Pixel{c,c,c,255});
    }
}
static void tiff(const QImage& image) {
    require(image.size() == QSize(3,2), "Wrong TIFF dimensions");
    const std::array<std::uint8_t,6> values{0,127,255,255,63,0};
    for (int y=0;y<2;++y) for (int x=0;x<3;++x) {
        const auto c=values[y*3+x]; pixel(image,x,y,Pixel{c,c,c,255});
    }
}
int main(int argc,char** argv) {
    QGuiApplication app(argc,argv);
    return checked([&] {
        require(argc == 3, "Expected case and fixture directory");
        const QString mode=QString::fromLocal8Bit(argv[1]);
        const QString dir=QString::fromLocal8Bit(argv[2])+"/";
        if (mode=="webp") allPixels(read(dir+"scene.webp","webp"));
        else if (mode=="scaled") {
            QImageReader reader(dir+"scene.webp");
            reader.setScaledSize(QSize(width*2,height*2)); const auto image=reader.read();
            require(image.size()==QSize(width*2,height*2), "QImageReader scaling failed");
            // QImageReader performs fallback scaling; WebP has no native ScaledSize option.
            for (int y : {6,18}) for (int x : {8,24}) pixel(image,x*2,y*2,expected(x,y),1);
        } else if (mode=="tga") {
            allPixels(read(dir+"top.tga","tga")); allPixels(read(dir+"bottom.tga","tga"));
        } else if (mode=="wbmp") wbmp(read(dir+"scene.wbmp","wbmp"));
        else if (mode=="tiff") tiff(read(dir+"scene.tiff","tiff"));
        else if (mode=="invalid") {
            for (const QString& extension : {QString("webp"),QString("tga"),QString("wbmp"),QString("tiff")}) {
                QImageReader reader(dir+"bad."+extension);
                require(reader.read().isNull(), "Truncated fixture accepted");
                require(reader.error()!=QImageReader::UnknownError, "Missing decoder error");
                reader.setFileName(dir+(extension=="tga" ? "top." : "scene.")+extension);
                const auto recovered=reader.read();
                if (extension=="wbmp") wbmp(recovered);
                else if (extension=="tiff") tiff(recovered);
                else allPixels(recovered);
            }
        } else if (mode=="writer") {
            QImage source(width,height,QImage::Format_RGBA8888);
            for (int y=0;y<height;++y) for (int x=0;x<width;++x) {
                const auto c=expected(x,y); source.setPixelColor(x,y,QColor(c[0],c[1],c[2],c[3]));
            }
            QImageWriter writer(dir+"written.webp","webp"); writer.setQuality(100);
            require(writer.canWrite() && writer.write(source), "Qt WebP writer failed");
        } else require(false,"Unknown case");
    });
}
