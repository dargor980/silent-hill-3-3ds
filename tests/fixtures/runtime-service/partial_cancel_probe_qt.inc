// Private test only: act after actual send plus the consumer's recv receipt.
#include "partial_cancel_probe.hpp"
#include <QAction>
#include <QCoreApplication>
#include <QThread>
#include <unistd.h>
namespace sh3_pc {
inline bool tick() {
  const char* ready=std::getenv("SH3_PARTIAL_READY");
  const char* route=std::getenv("SH3_PARTIAL_ROUTE");
  if (!sent.load() || !ready || !route || ::access(ready,F_OK)!=0 || !g_main_window)
    return false;
  if (QThread::currentThread()!=QCoreApplication::instance()->thread()) std::abort();
  trace("ui_action",sent.load());
  if (!std::strcmp(route,"window")) g_main_window->close();
  else if (!std::strcmp(route,"menu")) {
    auto* action=g_main_window->findChild<QAction*>(QStringLiteral("actionExit"));
    if (!action || !action->isEnabled()) std::abort();
    action->trigger();
  } else std::abort();
  trace("ui_return",sent.load());
  return true;
}
}
