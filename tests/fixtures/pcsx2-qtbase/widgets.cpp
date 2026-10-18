#include "fixture.hpp"
#include "ui_panel.h"
#include <QApplication>
#include <QWidget>

int main(int argc, char** argv) {
    QApplication app(argc, argv);
    return checked([&] {
        require(app.platformName() == "offscreen", "unexpected platform");
        QWidget panel;
        Ui::Panel ui;
        ui.setupUi(&panel);
        require(ui.message->text() == QString::fromUtf8("Espa\xc3\xb1ol: Normal"), "uic text mismatch");
        int count = 0;
        QObject::connect(ui.advance, &QPushButton::clicked, &panel,
            [&] { ui.message->setText(QString::number(++count)); });
        require(ui.advance->isEnabled(), "button unexpectedly disabled");
        ui.advance->click();
        require(count == 1 && ui.message->text() == "1", "widget interaction failed");
        ui.advance->setEnabled(false);
        ui.advance->click();
        require(count == 1, "disabled button invoked handler");
        ui.advance->setEnabled(true);
        ui.advance->click();
        require(count == 2 && ui.message->text() == "2", "re-enabled interaction failed");
    });
}
