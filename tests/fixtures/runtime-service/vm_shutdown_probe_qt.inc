// Included only in the private QtHost test copy after MainWindow.h.
#include "vm_shutdown_probe.hpp"
#include "../pcsx2/sh3-observer/pcsx2/runtime_service.hpp"
#include "GameList/GameListWidget.h"
#include <QAction>
#include <QApplication>
#include <QAbstractButton>
#include <QMessageBox>
#include <QThread>
#include <cstdlib>
#include <cstring>
namespace sh3_vs {
inline bool triggered{},clicked{};
inline void answer_dialog() {
  if (!triggered || clicked) return;
  const char* answer=std::getenv("SH3_VM_ANSWER");
  auto* box=qobject_cast<QMessageBox*>(QApplication::activeModalWidget());
  if (!answer || !box || !box->button(QMessageBox::Yes) || !box->button(QMessageBox::No)) return;
  const bool yes=!std::strcmp(answer,"yes");
  clicked=true;trace("dialog_click",yes);
  box->button(yes?QMessageBox::Yes:QMessageBox::No)->click();
}
inline bool tick() {
  static bool watching{};
  static std::chrono::steady_clock::time_point watch;
  const char* initial=std::getenv("SH3_VM_INITIAL");
  const char* route=std::getenv("SH3_VM_ROUTE");
  const char* answer=std::getenv("SH3_VM_ANSWER");
  if (!initial || !route || !answer || !g_main_window) return false;
  if (QThread::currentThread()!=QCoreApplication::instance()->thread()) std::abort();
  const bool paused=!std::strcmp(initial,"paused"),yes=!std::strcmp(answer,"yes");
  if (!triggered) {
    if (!QtHost::IsVMValid() || QtHost::IsVMPaused()!=paused ||
        (paused && !inventory.load())) return false;
    auto* action=g_main_window->findChild<QAction*>(QString::fromLatin1(
      !std::strcmp(route,"toolbar")?"actionToolbarPowerOff":"actionPowerOff"));
    if (!action || !action->isEnabled()) return false;
    triggered=true;trace("ui_action",paused);
    action->trigger();trace("ui_return");return false;
  }
  if (!clicked) return false;
  if (!decision || QApplication::activeModalWidget() ||
      !sh3::observer::pcsx2::runtime_service_finished()) return false;
  auto* list=g_main_window->findChild<GameListWidget*>();
  const bool expected=yes ? (!QtHost::IsVMValid() && list && list->isVisible()) :
    (QtHost::IsVMValid() && QtHost::IsVMPaused()==paused);
  if (!expected || !g_main_window->isVisible()) { watching=false;return false; }
  if (!watching) { watching=true;watch=std::chrono::steady_clock::now();trace("state_observed",yes);return false; }
  // An observation window after the expected state; not a phase-selection delay.
  if (std::chrono::steady_clock::now()-watch<std::chrono::seconds(1)) return false;
  trace(yes?"list_retained":"vm_retained",paused);
  trace("test_exit");
  // Explicit teardown only AFTER evidence of VM state and application survival.
  g_main_window->requestExit(false);
  return true;
}
}
