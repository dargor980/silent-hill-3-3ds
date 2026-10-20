"""Insert own UI cancellation hooks into the pinned private MainWindow source."""


def integrate(source: str) -> str:
    guard = "#if defined(SH3_ENABLE_OBSERVER) && defined(__APPLE__)\n"
    call = "sh3::observer::pcsx2::cancel_runtime_service_from_ui()"
    result = guard + '#include "../pcsx2/sh3-observer/pcsx2/runtime_service.hpp"\n#endif\n'
    result += source
    for signature in [
        "void MainWindow::requestExit(bool allow_confirm)",
        "void MainWindow::quit()",
    ]:
        old = signature + "\n{"
        assert result.count(old) == 1
        result = result.replace(old, old + "\n" + guard + f"    if ({call}) return;\n#endif")
    old = "void MainWindow::closeEvent(QCloseEvent* event)\n{"
    assert result.count(old) == 1
    return result.replace(
        old, old + "\n" + guard + f"    if ({call}) {{ event->ignore(); return; }}\n#endif"
    )
