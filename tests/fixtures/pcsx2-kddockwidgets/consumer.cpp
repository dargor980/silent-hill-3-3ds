#include <kddockwidgets/DockWidget.h>
#include <kddockwidgets/MainWindow.h>
#include <kddockwidgets/LayoutSaver.h>
#include <kddockwidgets/core/DockWidget.h>
#include <QApplication>
#include <QEvent>
#include <QJsonDocument>
#include <QLabel>
#include <QPointer>
#include <QSet>
#include <QTemporaryDir>
#include <QTest>
#include <cstdio>
#include <stdexcept>

static_assert(KDDW_FRONTEND_QTWIDGETS, "Qt Widgets frontend must be active");
namespace KD = KDDockWidgets;
using Dock = KD::QtWidgets::DockWidget;

void require(bool condition, const char *message)
{
    if (!condition)
        throw std::runtime_error(message);
}

void settle()
{
    QTest::qWait(30);
    QCoreApplication::sendPostedEvents(nullptr, QEvent::DeferredDelete);
    QCoreApplication::processEvents();
}

// Owns the scenario and its guest widgets; persistence and assertions are separate.
class Scenario {
public:
    KD::QtWidgets::MainWindow window{QStringLiteral("sh3-observer")};
    QPointer<Dock> scene{new Dock(QStringLiteral("scene"))};
    QPointer<Dock> resources{new Dock(QStringLiteral("resources"))};
    QPointer<Dock> log{new Dock(QStringLiteral("log"))};

    Scenario()
    {
        window.resize(1000, 700);
        scene->setWidget(new QLabel(QStringLiteral("Escena sintética")));
        resources->setWidget(new QLabel(QStringLiteral("Recursos sintéticos")));
        log->setWidget(new QLabel(QStringLiteral("Registro sintético")));
        window.addDockWidget(scene, KD::Location_OnLeft);
        window.addDockWidget(resources, KD::Location_OnRight, scene);
        window.addDockWidget(log, KD::Location_OnBottom, scene);
        window.show();
        settle();
    }

    ~Scenario()
    {
        delete log.data();
        delete resources.data();
        delete scene.data();
    }

    void savedState()
    {
        scene->addDockWidgetAsTab(resources);
        resources->setAsCurrentTab();
        log->setFloating(true);
        settle();
        expectSavedState();
    }

    void disturb()
    {
        resources->setFloating(true);
        scene->forceClose();
        log->forceClose();
        settle();
        require(resources->isFloating() && !scene->isOpen() && !log->isOpen(),
                "Layout was not changed before restore");
    }

    void expectSavedState() const
    {
        require(scene->uniqueName() == QStringLiteral("scene") &&
                    resources->uniqueName() == QStringLiteral("resources") &&
                    log->uniqueName() == QStringLiteral("log"), "Stable IDs changed");
        require(scene->isOpen() && resources->isOpen() && log->isOpen(), "Open states differ");
        require(!scene->isFloating() && !resources->isFloating() && log->isFloating(),
                "Docked/floating states differ");
        require(scene->group() && scene->group() == resources->group(), "Tab relation lost");
        require(resources->dockWidget()->isCurrentTab(), "Selected tab was not restored");
        require(scene->dockWidget()->mainWindow() == resources->dockWidget()->mainWindow() &&
                    scene->dockWidget()->mainWindow(), "Main window relation lost");
        require(qobject_cast<QLabel *>(scene->widget())->text() == QStringLiteral("Escena sintética"),
                "Guest contents changed");
    }
};

void verifyRestored(const KD::LayoutSaver &saver)
{
    QSet<QString> names;
    for (auto *dock : saver.restoredDockWidgets())
        names.insert(dock->uniqueName());
    require(names == QSet<QString>{QStringLiteral("scene"), QStringLiteral("resources"),
                                  QStringLiteral("log")}, "Restored IDs do not match");
    require(!KD::LayoutSaver::restoreInProgress(), "Restore remained active");
}

int main(int argc, char **argv)
{
    QApplication app(argc, argv);
    app.setQuitOnLastWindowClosed(false);
    KD::initFrontend(KD::FrontendType::QtWidgets);
    try {
        require(argc == 2, "Pass one test case");
        const QString test = QString::fromLocal8Bit(argv[1]);
        Scenario scenario;
        if (test == QStringLiteral("docking")) {
            require(scenario.scene->isOpen() && !scenario.scene->isFloating(), "Initial scene state");
            require(scenario.resources->isOpen() && !scenario.resources->isFloating(), "Initial resources state");
            require(scenario.scene->group() != scenario.resources->group(), "Initial groups should differ");
            require(scenario.scene->dockWidget()->mainWindow() == scenario.resources->dockWidget()->mainWindow(),
                    "Initial main window differs");
            require(qobject_cast<QLabel *>(scenario.resources->widget())->text() == QStringLiteral("Recursos sintéticos"),
                    "Resource guest missing");
            scenario.resources->setFloating(true);
            settle();
            require(scenario.resources->isOpen() && scenario.resources->isFloating(), "Float failed");
            scenario.resources->setFloating(false);
            settle();
            require(scenario.resources->isOpen() && !scenario.resources->isFloating(), "Redock failed");
        } else if (test == QStringLiteral("tabs")) {
            scenario.savedState();
            scenario.scene->setAsCurrentTab();
            settle();
            require(scenario.scene->dockWidget()->isCurrentTab() &&
                        !scenario.resources->dockWidget()->isCurrentTab(), "Tab switch failed");
            scenario.resources->setAsCurrentTab();
            settle();
            scenario.expectSavedState();
        } else if (test == QStringLiteral("lifecycle")) {
            auto *guest = scenario.resources->widget();
            require(scenario.resources->close(), "Close refused");
            settle();
            require(!scenario.resources->isOpen(), "Dock remained open");
            scenario.resources->open();
            settle();
            require(scenario.resources->isOpen() && !scenario.resources->isFloating() &&
                        scenario.resources->widget() == guest, "Reopen lost state or guest");
        } else {
            scenario.savedState();
            KD::LayoutSaver saver;
            const auto bytes = saver.serializeLayout();
            require(!bytes.isEmpty() && QJsonDocument::fromJson(bytes).isObject(), "Invalid serialized layout");
            QTemporaryDir temp;
            require(temp.isValid(), "Temporary directory failed");
            const auto file = temp.filePath(QStringLiteral("layout.json"));
            require(saver.saveToFile(file), "Save to file failed");
            scenario.disturb();
            if (test == QStringLiteral("memory")) {
                require(saver.restoreLayout(bytes), "Memory restore failed");
            } else if (test == QStringLiteral("file")) {
                require(saver.restoreFromFile(file), "File restore failed");
            } else if (test == QStringLiteral("invalid")) {
                require(!saver.restoreLayout(QByteArrayLiteral("{broken-json")), "Malformed JSON accepted");
                require(!saver.restoreLayout(QByteArrayLiteral("{}")), "Missing layout fields accepted");
                require(saver.restoreLayout(bytes), "Recovery after invalid layout failed");
            } else if (test == QStringLiteral("missing")) {
                require(!saver.restoreFromFile(temp.filePath(QStringLiteral("absent.json"))), "Missing file accepted");
                require(saver.restoreFromFile(file), "Recovery after missing file failed");
            } else {
                throw std::runtime_error("Unknown case");
            }
            settle();
            scenario.expectSavedState();
            verifyRestored(saver);
        }
        std::printf("PASS %s\n", argv[1]);
    } catch (const std::exception &error) {
        std::fprintf(stderr, "FAIL: %s\n", error.what());
        return 1;
    }
    return 0;
}
