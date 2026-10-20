"""Exact, fail-closed insertions into private copies of six source units."""


def apply(name, source):
    def change(old, new):
        nonlocal source
        if source.count(old) != 1:
            raise ValueError(f"ambiguous timing anchor: {name}: {old!r}")
        source = source.replace(old, new)

    def before(anchor, code):
        change(anchor, code + anchor)

    def after(anchor, code):
        change(anchor, anchor + code)

    if name == "macos_diagnostic_work.cpp":
        after(
            "  Reason prepare(DiagnosticBudget&) override {",
            "\n    sh3_it::Span it(sh3_it::prepare);",
        )
        before("      source_ =", "      sh3_it::Span parse(sh3_it::manifest_parse);\n")
        after(
            "if(result != LaunchFailure::none) return fail(Reason::configuration);",
            "\n      parse.done();",
        )
        before(
            "    inventory_ = std::make_unique<Inventory>",
            "    sh3_it::Span construct(sh3_it::construct);\n",
        )
        after("    if(details_) details_->prepared=true;", "\n    construct.done(); it.done();")
        after(
            "  Reason sample(DiagnosticBudget&, DiagnosticObservation& out) override {",
            "\n    sh3_it::data.next(); sh3_it::Span it(sh3_it::sample);",
        )
        after(
            "    out.inventory = result; // No runtime guard binding: "
            "facts and epochs stay unknown/zero.",
            "\n    it.done();",
        )
        after("  bool close() noexcept override {", "\n    sh3_it::Span it(sh3_it::close_work);")
        before(
            "    return close_ok_;", '    if(close_ok_) it.done(); it.stop(); sh3_it::dump("DW");\n'
        )
    elif name == "platform_inventory.cpp":
        after(
            "PlatformInventoryResult PlatformInventoryGuard::sample() noexcept {",
            "\n  sh3_it::Span initial(sh3_it::initial);",
        )
        before(
            "  const auto files = manifest_.sample();",
            "  initial.done(); initial.stop();\n  sh3_it::Span mb(sh3_it::manifest_before);\n",
        )
        before("  auto& observed =", "  mb.done(); mb.stop();\n")
        after(
            "  for (unsigned pass=0;pass<2;++pass) {",
            "\n    sh3_it::Span origin(pass ? sh3_it::origin_second : sh3_it::origin_first);",
        )
        after("      observed[i] = origin;\n    }", "\n    origin.done();")
        before("  const auto after_files =", "  sh3_it::Span ma(sh3_it::manifest_after);\n")
        before(
            "  const bool slices =",
            "  ma.done(); ma.stop();\n  sh3_it::Span digest(sh3_it::digest);\n",
        )
        before(
            "  if (!images_.read(last))",
            "  digest.done(); digest.stop();\n  sh3_it::Span tail(sh3_it::tail);\n",
        )
        before("  baseline_ = result; ready_ = true; return result;", "  tail.done();\n")
    elif name == "macos_artifact_manifest.cpp":
        after(
            "bool MacOSSha256::update(const void* bytes, std::size_t size) noexcept {",
            "\n  sh3_it::Span it(sh3_it::sha_update,true);",
        )
        # Record bytes actually submitted to CommonCrypto; return path unchanged.
        after(
            "  active_ = CC_SHA256_Update(&context_, bytes, static_cast<CC_LONG>(size)) == 1;",
            "\n  if(active_) it.done(size);",
        )
        after(
            "    bool read(FileObject& out) noexcept override {",
            "\n      sh3_it::Span it(sh3_it::file_identity,true);",
        )
        after("      out = held;", "\n      it.done();")
        after(
            "    bool read_at(std::uint64_t offset, void* bytes, std::size_t wanted, "
            "std::size_t& got) noexcept override {",
            "\n      sh3_it::Span it(sh3_it::file_read,true);",
        )
        after("      got = static_cast<std::size_t>(n);", "\n      it.done(got);")
    elif name == "macos_platform_origin.cpp":
        after(
            "bool MacOSPlatformOrigins::stable() noexcept {",
            "\n  sh3_it::Span it(sh3_it::origin_stable,true);",
        )
        # The last return still executes the ordinary checkpoint exactly once.
        before("  return active(InspectionStep::images);", "  it.done();\n")
    elif name == "diagnostic_worker.cpp":
        after(
            "  s.deadline = external ? std::min(*external, now+duration) : now+duration;",
            '\n  sh3_it::mark("submit",unsigned(request.sequence),sh3_it::ns(s.deadline),'
            "sh3_it::ns(now));",
        )
    elif name == "runtime_service.cpp":
        after("void run(Configuration c) noexcept {", "\n  sh3_it::calibrate();")
        after(
            "      const auto opened=Clock::now(), deadline=opened+5s;",
            '\n      sh3_it::mark("open",0,sh3_it::ns(deadline),sh3_it::ns(opened));',
        )
        after(
            "          if (binding && reason==Reason::none && !cancelled.load()) {",
            '\n            sh3_it::mark("binding");',
        )
        change(
            "if (result==RuntimeSessionResult::complete) ++replies;",
            "if (result==RuntimeSessionResult::complete) { ++replies; "
            'sh3_it::mark("delivered",replies); }',
        )
        before("  if (handoff) handoff->cancel(reason", '  sh3_it::mark("cleanup_begin");\n')
        before(
            "  // Telemetry is read only after DW has joined.",
            '  sh3_it::mark("cleanup_end"); sh3_it::dump("IO");\n',
        )
    else:
        raise ValueError(f"unsupported timing unit: {name}")
    return '#include "inventory_timing_probe.hpp"\n' + source


UNITS = (
    "native/macos_diagnostic_work.cpp",
    "platform_inventory.cpp",
    "native/macos_artifact_manifest.cpp",
    "native/macos_platform_origin.cpp",
    "diagnostic_worker.cpp",
    "pcsx2/runtime_service.cpp",
)
