#include "emitter.hpp"
#include "fixture.hpp"
#include <QCoreApplication>
#include <QEventLoop>
#include <QFile>
#include <QJsonDocument>
#include <QJsonObject>
#include <QTimer>

static void signalCase() {
    Emitter sender;
    QEventLoop loop;
    int calls = 0, received = 0;
    bool timedOut = false;
    const auto connection = QObject::connect(&sender, &Emitter::delivered,
        &loop, [&](int value) { ++calls; received = value; loop.quit(); },
        Qt::QueuedConnection);
    QTimer timeout;
    timeout.setSingleShot(true);
    QObject::connect(&timeout, &QTimer::timeout, &loop,
        [&] { timedOut = true; loop.quit(); });
    timeout.start(3000);
    sender.publish(37);
    require(calls == 0, "queued signal delivered synchronously");
    loop.exec();
    timeout.stop();
    require(!timedOut && calls == 1 && received == 37, "queued signal failed");
    require(QObject::disconnect(connection), "disconnect failed");
    sender.publish(42);
    QCoreApplication::processEvents();
    require(calls == 1, "disconnected receiver invoked");
}

static void jsonCase() {
    const QByteArray utf8("Espa\xc3\xb1ol: acci\xc3\xb3n y acertijos");
    const QString value = QString::fromUtf8(utf8);
    require(value.toUtf8() == utf8, "UTF-8 roundtrip failed");
    const QJsonDocument input(QJsonObject{{"label", value}, {"count", 37}});
    QJsonParseError error;
    const auto decoded = QJsonDocument::fromJson(input.toJson(QJsonDocument::Compact), &error);
    require(error.error == QJsonParseError::NoError && decoded == input, "JSON roundtrip failed");
    require(decoded.object()["label"].toString() == value, "JSON Unicode lost");
    const auto invalid = QJsonDocument::fromJson("{\"count\":]", &error);
    require(invalid.isNull() && error.error != QJsonParseError::NoError
        && !error.errorString().isEmpty(), "invalid JSON accepted");
}

static void resourceCase() {
    QFile resource(":/qb/message.txt");
    require(resource.open(QIODevice::ReadOnly), "rcc resource missing");
    require(resource.readAll() == QByteArray("Recurso propio: espa\xc3\xb1ol.\n"), "resource content changed");
    QFile absent(":/qb/absent.txt");
    require(!absent.open(QIODevice::ReadOnly), "absent resource accepted");
}

int main(int argc, char** argv) {
    QCoreApplication app(argc, argv);
    return checked([&] {
        require(argc == 2, "expected one case name");
        require(QByteArray(qVersion()) == "6.11.1", "unexpected runtime Qt version");
        const std::string_view name(argv[1]);
        if (name == "signals") signalCase();
        else if (name == "json") jsonCase();
        else if (name == "resources") resourceCase();
        else throw std::runtime_error("unknown case");
    });
}
