// Only in private QtHost copy, after declarations of MainWindow and Host.
#include "host_callback_probe.hpp"
#include <QAction>
namespace sh3_hc {
inline void tick() {
  static bool sent{};
  if (sent || mode()!=Mode::late_cancel || !held.load() || !g_main_window) return;
  auto* action=g_main_window->findChild<QAction*>(QStringLiteral("actionExit"));
  if (!action || !action->isEnabled()) std::abort();
  sent=true;trace("ui_action");action->trigger();trace("ui_return");
}
}
