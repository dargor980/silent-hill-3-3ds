"""Own insertions into pinned private MainWindow/QtHost copies, after SRC124."""


def main_window(source: str) -> str:
    signature = (
        "bool MainWindow::requestShutdown(bool allow_confirm, "
        "bool allow_save_to_state, bool default_save_to_state)\n{"
    )
    assert source.count(signature) == 1
    return source.replace(
        signature,
        signature
        + "\n#if defined(SH3_ENABLE_OBSERVER) && defined(__APPLE__)\n"
        + "    if (s_vm_valid && sh3::observer::pcsx2::defer_runtime_vm_shutdown(\n"
        + "        {allow_confirm,allow_save_to_state,default_save_to_state})) return false;\n"
        + "#endif",
    )


def qt_host(source: str) -> str:
    old = """            if (sh3::observer::pcsx2::runtime_service_finished())
            {
                observer_timer.stop();
                QCoreApplication::exit(EXIT_SUCCESS);
            }"""
    assert source.count(old) == 1
    return source.replace(
        old,
        """            using namespace sh3::observer::pcsx2;
            RuntimeVMShutdownRequest request;
            const auto action=poll_runtime_service_ui(request);
            if (action!=RuntimeServiceUIAction::none)
            {
                observer_timer.stop();
                if (action==RuntimeServiceUIAction::exit_application)
                    QCoreApplication::exit(EXIT_SUCCESS);
                else if (g_main_window)
                    g_main_window->requestShutdown(request.allow_confirm,
                        request.allow_save_to_state,request.default_save_to_state);
            }""",
    )
