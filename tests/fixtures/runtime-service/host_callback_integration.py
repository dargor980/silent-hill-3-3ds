"""Validation-only insertions into the immutable SRC126 private source overlay."""


def replace(source: str, old: str, new: str) -> str:
    assert source.count(old) == 1, old
    return source.replace(old, new)


def frontend(source: str) -> str:
    source = '#include "host_callback_probe.hpp"\n' + source
    source = replace(
        source,
        "    return VMManager::Internal::QueueObserverRuntimeDiagnosticUntil(id, deadline);",
        """    sh3_hc::trace("queue_entry",unsigned(id),VMManager::Internal::IsObserverCpuThread());
    auto ticket=VMManager::Internal::QueueObserverRuntimeDiagnosticUntil(id, deadline);
    sh3_hc::trace("queue_result",bool(ticket),VMManager::Internal::IsObserverCpuThread());
    return ticket;""",
    )
    return replace(
        source,
        """    Host::RunOnCPUThread([handoff] {
      CpuQueue queue;
      handoff->execute(queue);
    }, false);""",
        """    sh3_hc::remember(handoff);
    const auto callback=[handoff](unsigned ordinal) {
      return [handoff,ordinal] {
        sh3_hc::ordinal=ordinal;
        sh3_hc::trace("callback_begin",0,VMManager::Internal::IsObserverCpuThread());
        CpuQueue queue;
        const bool accepted=handoff->execute(queue);
        sh3_hc::trace("callback_result",accepted,VMManager::Internal::IsObserverCpuThread());
        sh3_hc::trace("callback_reason",unsigned(handoff->failure()));
        sh3_hc::trace("callback_binding",bool(handoff->binding()));
        sh3_hc::trace("callback_end");sh3_hc::ordinal=0;
      };
    };
    const auto dispatch=[callback](unsigned ordinal) {
      sh3_hc::trace("dispatch",ordinal);
      Host::RunOnCPUThread(callback(ordinal),false);
    };
    const auto mode=sh3_hc::mode();
    if (mode==sh3_hc::Mode::late_cancel || mode==sh3_hc::Mode::late_deadline)
      sh3_hc::retain([dispatch]{dispatch(1);});
    else {
      dispatch(1);
      if (mode==sh3_hc::Mode::duplicate_active) dispatch(2);
      else sh3_hc::retain([dispatch]{dispatch(2);});
    }""",
    )


def service(source: str) -> str:
    source = '#include "host_callback_probe.hpp"\n' + source
    pairs = [
        (
            "run(std::move(c));finished=true;",
            "run(std::move(c));sh3_hc::after_io();finished=true;",
        ),
        (
            "void cancel_runtime_service() noexcept { cancelled=true; }",
            'void cancel_runtime_service() noexcept { sh3_hc::trace("cancel_ui");cancelled=true; }',
        ),
        (
            "  if (io.joinable()) io.join();",
            '  if (io.joinable()) { io.join();sh3_hc::trace("io_joined"); }',
        ),
        (
            "  if (worker) worker->cancel();",
            '  if (handoff) sh3_hc::trace("revoked",unsigned(handoff->failure()));\n'
            "  if (worker) worker->cancel();",
        ),
        (
            "    if (worker) {",
            '    sh3_hc::trace("cpu_quiescent");\n    if (worker) {',
        ),
        (
            "  // Telemetry is read only after DW has joined.",
            '  if (worker && worker->status().joined) sh3_hc::trace("dw_joined");\n'
            "  // Telemetry is read only after DW has joined.",
        ),
    ]
    for old, new in pairs:
        source = replace(source, old, new)
    return source


def qt_host(source: str) -> str:
    source = replace(
        source,
        '#include "QtHost.h"',
        '#include "QtHost.h"\n#include "host_callback_probe_qt.inc"',
    )
    source = replace(
        source,
        "            RuntimeVMShutdownRequest request;",
        "            sh3_hc::tick();\n            RuntimeVMShutdownRequest request;",
    )
    return replace(
        source,
        "\tEmuThread::stop();",
        '\tsh3_hc::trace("cpu_stop_begin");\n\tEmuThread::stop();\n'
        '\tsh3_hc::trace("cpu_stop_end");\n'
        '\tsh3_hc::trace("final_expired",sh3_hc::expired());',
    )
