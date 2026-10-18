#include "fixture.hpp"
#include <QCoreApplication>
#include <QTranslator>

int main(int argc, char** argv) {
    QCoreApplication app(argc, argv);
    return checked([&] {
        require(argc == 4, "Expected case, QM and invalid QM");
        QTranslator translator;
        const QString mode=QString::fromLocal8Bit(argv[1]);
        require(mode=="translation" || mode=="recovery", "Unknown case");
        if (mode=="recovery") {
            require(!translator.load(QString::fromLocal8Bit(argv[3])), "Invalid QM accepted");
            require(translator.isEmpty(), "Invalid translator not empty");
        }
        require(translator.load(QString::fromLocal8Bit(argv[2])), "Valid QM rejected");
        require(app.installTranslator(&translator), "Translator installation failed");
        require(QCoreApplication::translate("Fixture","Open door","action")==QStringLiteral("Abrir puerta"), "Wrong action");
        require(QCoreApplication::translate("Fixture","Key","item")==QStringLiteral("Llave"), "Wrong item");
        require(QCoreApplication::translate("Fixture","Key","keyboard")==QStringLiteral("Tecla"), "Wrong keyboard key");
        require(QCoreApplication::translate("Fixture","Moon: 🌙")==QStringLiteral("Brújula: 🌙"), "Wrong Unicode");
        for (int count : {0,1,2,5}) {
            const auto wanted=QString::number(count)+(count==1 ? QStringLiteral(" llave") : QStringLiteral(" llaves"));
            require(QCoreApplication::translate("Fixture","%n key(s)",nullptr,count)==wanted, "Wrong plural");
        }
        require(QCoreApplication::translate("Other","Open door","action")==QStringLiteral("Open door"), "Context fallback failed");
        require(QCoreApplication::translate("Fixture","Unknown")==QStringLiteral("Unknown"), "Missing message fallback failed");
        require(app.removeTranslator(&translator), "Translator removal failed");
        require(QCoreApplication::translate("Fixture","Key","item")==QStringLiteral("Key"), "Removal fallback failed");
    });
}
