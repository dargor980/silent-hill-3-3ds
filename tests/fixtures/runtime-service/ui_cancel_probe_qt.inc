// Included only in the private QtHost validation copy, after MainWindow.h.
#include "ui_cancel_probe.hpp"
#include <QAction>
#include <QCoreApplication>
#include <QThread>
#include <unistd.h>
namespace sh3_uc {
inline bool tick() {
  const char* target = std::getenv("SH3_UI_CANCEL_PHASE");
  const char* route = std::getenv("SH3_UI_CANCEL_ROUTE");
  if (!target || !route) return false;
  const unsigned wanted = !std::strcmp(target,"waiting") ? 1 :
    !std::strcmp(target,"inventory") ? 2 : !std::strcmp(target,"release") ? 3 : 0;
  if (!wanted || phase.load()!=wanted || !g_main_window) return false;
  if (wanted==3) {
    const char* ready=std::getenv("SH3_UI_CANCEL_READY");
    if (!ready || ::access(ready,F_OK)!=0) return false;
  }
  if (QThread::currentThread()!=QCoreApplication::instance()->thread()) std::abort();
  trace("ui_action",phase.load());
  if (!std::strcmp(route,"window")) g_main_window->close();
  else if (!std::strcmp(route,"menu")) {
    auto* action=g_main_window->findChild<QAction*>(QStringLiteral("actionExit"));
    if (!action || !action->isEnabled()) std::abort();
    action->trigger();
  } else std::abort();
  trace("ui_return",phase.load());
  return true;
}
} // namespace sh3_uc
