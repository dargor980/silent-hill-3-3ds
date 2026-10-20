"""Reversible hooks for the IC diagnostic candidate, never an admission change."""
# ruff: noqa: E501 -- Keep the embedded C++ format identical to the tested fixture.

EMITTER = r"""
void emit_census(const char* phase, const probe::CensusObservation& s,
                 bool wrapper_ok, bool original_ok) noexcept {
  std::fprintf(stderr,
    "SH3_CENSUS phase=%s complete=%u original_ok=%u events=%zu adds=%zu removes=%zu active=%zu peak=%zu boundary_event=%zu boundary_kind=%u boundary_address=%llx failure=%u\n",
    phase,unsigned(wrapper_ok && s.failure==probe::CensusFailure::none),unsigned(original_ok),
    s.events,s.adds,s.removes,s.active,s.peak,s.boundary_event,unsigned(s.boundary_kind),
    static_cast<unsigned long long>(s.boundary_address),unsigned(s.failure));
}
"""

EXPORT = r"""
void probe::dump_image_census(const char* phase) noexcept {
  auto& events = registry();
  if (events.owner.load()!=getpid() || events.failed.load()) return;
  if (pthread_mutex_lock(&events.mutex)!=0) { events.failed.store(true); return; }
  const auto census = events.census.observation();
  ImageSnapshot original{};
  const bool original_ok = events.ledger.read(original);
  if (pthread_mutex_unlock(&events.mutex)!=0) events.failed.store(true);
  emit_census(phase,census,!events.failed.load(),original_ok && !events.failed.load());
}
"""


def replace_reversibly(source, edits):
    original = source
    for before, after in edits:
        assert source.count(before) == 1, before
        source = source.replace(before, after)
    check = source
    for before, after in reversed(edits):
        assert check.count(after) == 1, after
        check = check.replace(after, before)
    assert check == original
    return source


def patch_events(source):
    return replace_reversibly(
        source,
        [
            (
                '#include "sh3_observer/macos_image_identity.hpp"',
                '#include "sh3_observer/macos_image_identity.hpp"\n'
                '#include "sh3_observer/image_census_probe.hpp"\n'
                '#include "sh3_observer/census_report_probe.hpp"\n#include <cstdio>',
            ),
            ("  ImageLedger ledger{};", "  ImageLedger ledger{};\n  probe::ImageCensus census{};"),
            (
                "  if (added) events.ledger.add(address); else events.ledger.remove(address);",
                "  if (added) events.census.add(address); else events.census.remove(address);\n"
                "  if (added) events.ledger.add(address); else events.ledger.remove(address);",
            ),
            ("void register_events() {", EMITTER + "void register_events() {"),
            (
                "  const bool ok = events.ledger.read(output);",
                "  const auto census = events.census.observation();\n"
                "  const bool ok = events.ledger.read(output);",
            ),
            (
                "  if (!ok || events.failed.load()) { output = {}; return false; }",
                '  emit_census("read",census,!events.failed.load(),ok && !events.failed.load());\n'
                "  if (!ok || events.failed.load()) { output = {}; return false; }",
            ),
            ("} // namespace sh3::observer", EXPORT + "} // namespace sh3::observer"),
        ],
    )


def patch_qt(source):
    return replace_reversibly(
        source,
        [
            (
                '#include "../pcsx2/sh3-observer/pcsx2/runtime_service.hpp"',
                '#include "../pcsx2/sh3-observer/pcsx2/runtime_service.hpp"\n'
                '#include "../pcsx2/sh3-observer/include/sh3_observer/census_report_probe.hpp"',
            ),
            (
                "\t// Shutting down.\n\tEmuThread::stop();",
                "\t// Shutting down.\n\tEmuThread::stop();\n"
                "#if defined(SH3_ENABLE_OBSERVER) && defined(__APPLE__)\n"
                '    sh3::observer::probe::dump_image_census("cpu_stopped");\n'
                "#endif",
            ),
        ],
    )
