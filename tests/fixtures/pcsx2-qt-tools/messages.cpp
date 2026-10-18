// Original extraction input; no game text.
#include <QCoreApplication>
void extractableMessages(int count) {
    (void)QCoreApplication::translate("Fixture", "Open door", "action");
    (void)QCoreApplication::translate("Fixture", "Key", "item");
    (void)QCoreApplication::translate("Fixture", "Key", "keyboard");
    (void)QCoreApplication::translate("Fixture", "Moon: 🌙");
    (void)QCoreApplication::translate("Fixture", "%n key(s)", nullptr, count);
}
