#include "fixture.hpp"
#include <QApplication>
#include <QFile>
#include <QLabel>
#include <QPushButton>
#include <QUiLoader>
#include <memory>

int main(int argc, char** argv) {
    QApplication app(argc,argv);
    return checked([&] {
        require(argc==4, "Expected case, valid UI and invalid UI");
        QUiLoader loader;
        const QString mode=QString::fromLocal8Bit(argv[1]);
        require(mode=="ui" || mode=="invalid-ui", "Unknown case");
        if (mode=="invalid-ui") {
            QFile invalid(QString::fromLocal8Bit(argv[3])); require(invalid.open(QIODevice::ReadOnly), "Missing invalid UI");
            std::unique_ptr<QWidget> rejected(loader.load(&invalid));
            require(!rejected && !loader.errorString().isEmpty(), "Malformed UI accepted or no diagnostic");
        }
        QFile valid(QString::fromLocal8Bit(argv[2])); require(valid.open(QIODevice::ReadOnly), "Missing valid UI");
        std::unique_ptr<QWidget> panel(loader.load(&valid));
        require(panel && panel->objectName()=="fixturePanel", "Failed to load form");
        require(panel->windowTitle()==QStringLiteral("Panel de prueba"), "Wrong title");
        auto* label=panel->findChild<QLabel*>("label"); auto* button=panel->findChild<QPushButton*>("button");
        require(label && label->text()==QStringLiteral("Brújula y llaves"), "Wrong label");
        require(button && button->text()==QStringLiteral("Abrir puerta") && button->isEnabled(), "Wrong button");
        int clicks=0; QObject::connect(button,&QPushButton::clicked,panel.get(),[&] {++clicks;});
        button->click(); require(clicks==1, "Loaded control did not emit signal");
        button->setEnabled(false); button->click(); require(clicks==1, "Disabled control emitted signal");
    });
}
