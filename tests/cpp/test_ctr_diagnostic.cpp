#include "check.hpp"
#include "diagnostic.hpp"
#include "memory_files.hpp"
#include "resource_sdk.hpp"
#include "sdk.hpp"
#include "sh3/application/options_store.hpp"
#include <algorithm>
#include <array>
#include <cstdio>
#include <string>
#include <unistd.h>

namespace {
MemoryFiles files;
struct Run {
    int code;
    std::string output;
};

// Capture the real stdio path used by the adapter. POSIX is available on both
// supported host runners; no console pixels or SDK execution are simulated here.
Run run() {
    CHECK(std::fflush(stdout) == 0);
    const int saved = dup(fileno(stdout));
    CHECK(saved >= 0);
    auto *capture = std::tmpfile();
    CHECK(capture != nullptr);
    CHECK(dup2(fileno(capture), fileno(stdout)) >= 0);
    const int code = sh3::platform::ctr::run_diagnostic(files, files);
    CHECK(std::fflush(stdout) == 0);
    CHECK(dup2(saved, fileno(stdout)) >= 0);
    CHECK(close(saved) == 0);
    std::rewind(capture);
    std::string output;
    std::array<char, 512> buffer{};
    while (const auto size = std::fread(buffer.data(), 1, buffer.size(), capture)) {
        output.append(buffer.data(), size);
    }
    CHECK(std::ferror(capture) == 0);
    CHECK(std::fclose(capture) == 0);
    const auto &s = ctr_test::sdk();
    CHECK(!s.gfx && !s.c3d && !s.c2d && !s.target && !s.tone && !s.frame && !s.callback);
    CHECK(!s.pending_gpu);
    return {code, output};
}

void check_success_cleanup() {
    const std::vector<std::string> expected{
        "gfx.init",      "console.init", "c3d.init",    "c2d.init",    "c2d.prepare",
        "target.create", "tone.init",    "hook.attach", "hook.detach", "tone.fini",
        "target.delete", "c2d.fini",     "c3d.fini",    "gfx.exit"};
    CHECK(ctr_test::sdk().resources == expected);
}

void check_frame(unsigned index, u32 color) {
    const auto &rects = ctr_test::sdk().rectangles;
    CHECK(index * 2 + 1 < rects.size());
    const auto &outer = rects[index * 2];
    CHECK(outer.x == 40 && outer.y == 40 && outer.z == 0);
    CHECK(outer.width == 320 && outer.height == 160 && outer.color == color);
    const auto &inner = rects[index * 2 + 1];
    CHECK(inner.x == 80 && inner.y == 80 && inner.z == 0);
    CHECK(inner.width == 80 && inner.height == 80);
    CHECK(inner.color == C2D_Color32(30, 30, 40, 255));
}

void failure(ctr_test::Failure stage, const char *name, bool exit_by_apt = false) {
    auto &s = ctr_test::sdk();
    s.failure = stage;
    // A cannot dismiss an initialization error; START or apt exit can.
    s.keys = exit_by_apt ? std::vector<u32>{KEY_A} : std::vector<u32>{KEY_A, KEY_START};
    const auto result = run();
    CHECK(result.code == 1);
    CHECK(files.reads == 0 && files.writes == 0);
    CHECK(result.output == std::string("GRAPHICS_INIT_FAILED\nStage: ") + name +
                               "\nBuild: host-contract\nSTART to exit\n");
    CHECK(s.begins == 0 && s.ends == 0 && s.rectangles.empty());
    CHECK(s.pauses.empty());
    CHECK(s.flushes == 1 && s.swaps == 1 && s.waits == 1);
    CHECK(s.scans == s.keys.size() && s.reads == s.keys.size());
    std::vector<std::string> expected{"gfx.init", "console.init", "c3d.init"};
    if (stage != ctr_test::Failure::citro3d) {
        expected.emplace_back("c2d.init");
        if (stage == ctr_test::Failure::target) {
            expected.insert(expected.end(), {"c2d.prepare", "target.create", "c2d.fini"});
        }
        expected.emplace_back("c3d.fini");
    }
    expected.emplace_back("gfx.exit");
    CHECK(s.resources == expected);
}
void setup_lifecycle(const std::string &scenario) {
    auto &s = ctr_test::sdk();
    if (scenario == "lifecycle_home_running" || scenario == "lifecycle_home_paused" ||
        scenario == "lifecycle_home_muted") {
        if (scenario == "lifecycle_home_muted") {
            files.record(MemoryFiles::Id::options_a, false, 1);
        }
        s.keys = {scenario == "lifecycle_home_paused" ? KEY_A : 0, 0, KEY_START};
        s.hook_batches = {{}, {APTHOOK_ONSUSPEND, APTHOOK_ONRESTORE}};
    } else if (scenario == "lifecycle_duplicate_hooks") {
        s.keys.assign(184, 0);
        s.keys.front() = KEY_SELECT;
        s.keys.back() = KEY_START;
        s.hook_batches.resize(183);
        s.hook_batches[181] = {APTHOOK_ONRESTORE, APTHOOK_ONWAKEUP};
        s.hook_batches[182] = {APTHOOK_ONSUSPEND, APTHOOK_ONSUSPEND, APTHOOK_ONRESTORE,
                               APTHOOK_ONRESTORE};
    } else if (scenario == "lifecycle_exit_batch") {
        s.keys = {KEY_X | KEY_SELECT | KEY_A};
        s.hook_batches = {{APTHOOK_ONEXIT, APTHOOK_ONSLEEP, APTHOOK_ONWAKEUP, APTHOOK_ONSUSPEND,
                           APTHOOK_ONRESTORE, APTHOOK_ONEXIT}};
    } else if (scenario == "lifecycle_close_suspended") {
        s.keys = {0, KEY_X};
        s.hook_batches = {{}, {APTHOOK_ONSLEEP}};
        s.apt_close_loop = 2;
    } else if (scenario == "lifecycle_suspended_input") {
        s.keys = {0, KEY_X | KEY_A | KEY_SELECT | KEY_START, KEY_X | KEY_Y | KEY_SELECT, 0,
                  KEY_START};
        s.hook_batches = {{}, {APTHOOK_ONSUSPEND}, {APTHOOK_ONSUSPEND}, {APTHOOK_ONRESTORE}};
    } else if (scenario == "lifecycle_resume_keys") {
        constexpr auto buttons = KEY_A | KEY_X | KEY_Y | KEY_SELECT | KEY_START;
        s.keys = {KEY_A, buttons, 0, 0, KEY_A, KEY_START};
        s.held = {KEY_A, buttons, buttons, 0, KEY_A, KEY_START};
        s.hook_batches = {{}, {APTHOOK_ONSLEEP, APTHOOK_ONWAKEUP}};
    } else if (scenario == "lifecycle_reserved_chords") {
        s.keys = {KEY_L | KEY_DOWN, KEY_SELECT | KEY_START | KEY_X | KEY_Y | KEY_A, 0, 0, KEY_X, 0,
                  KEY_START};
        s.held = {KEY_L | KEY_DOWN, KEY_L | KEY_DOWN | s.keys[1], KEY_SELECT, 0, KEY_X, 0,
                  KEY_START};
    } else if (scenario == "lifecycle_options_home") {
        s.keys = {KEY_X, 0, KEY_START};
        s.hook_batches = {{}, {APTHOOK_ONSUSPEND, APTHOOK_ONRESTORE}};
    } else {
        CHECK(false);
    }
}

void check_lifecycle(const std::string &scenario, const Run &result) {
    const auto &s = ctr_test::sdk();
    if (scenario == "lifecycle_home_running" || scenario == "lifecycle_home_paused" ||
        scenario == "lifecycle_home_muted") {
        const bool paused = scenario != "lifecycle_home_running";
        CHECK(s.pauses == (std::vector<bool>{paused, true, paused}));
        CHECK(s.input_loops == (std::vector<unsigned>{1, 2, 3}));
        CHECK(s.frame_loops == (std::vector<unsigned>{1, 2}));
        CHECK(files.writes == 0 && ctr_test::resource_sdk().samples == 2);
        const auto color = scenario == "lifecycle_home_paused" ? C2D_Color32(230, 160, 40, 255)
                                                               : C2D_Color32(60, 200, 120, 255);
        check_frame(0, color);
        check_frame(1, color);
    } else if (scenario == "lifecycle_duplicate_hooks") {
        CHECK(ctr_test::resource_sdk().samples == 5 && files.writes == 0);
        CHECK(s.pauses.size() == 184);
        CHECK(std::count(s.pauses.begin(), s.pauses.end(), true) == 1);
        const auto last = result.output.substr(result.output.rfind("SH3 resources"));
        CHECK(last.find("warmup: 59") != std::string::npos);
        CHECK(last.find("Begin wait+SDK    UNKNOWN") != std::string::npos);
    } else if (scenario == "lifecycle_exit_batch") {
        CHECK(s.reads == 0 && s.begins == 0 && files.writes == 0);
        CHECK(ctr_test::resource_sdk().samples == 0 && s.pauses == std::vector<bool>{true});
    } else if (scenario == "lifecycle_close_suspended") {
        CHECK(s.input_loops == std::vector<unsigned>{1} &&
              s.frame_loops == std::vector<unsigned>{1});
        CHECK(files.writes == 0 && s.pauses == (std::vector<bool>{false, true}));
    } else if (scenario == "lifecycle_suspended_input") {
        CHECK(s.input_loops == (std::vector<unsigned>{1, 4, 5}));
        CHECK(s.frame_loops == (std::vector<unsigned>{1, 4}));
        CHECK(files.writes == 0 && s.clears == 0);
        CHECK(result.output.find("State: paused") == std::string::npos);
    } else if (scenario == "lifecycle_resume_keys") {
        CHECK(s.reads == 6 && s.begins == 5 && files.writes == 0 && s.clears == 0);
        CHECK(result.output.find("Release all buttons to enable controls") != std::string::npos);
        for (unsigned i = 0; i < 4; ++i) {
            check_frame(i, C2D_Color32(230, 160, 40, 255));
        }
        check_frame(4, C2D_Color32(60, 200, 120, 255));
    } else if (scenario == "lifecycle_reserved_chords" || scenario == "lifecycle_options_home") {
        CHECK(files.writes == 1 && s.clears == 0);
        CHECK(s.reads == (scenario == "lifecycle_reserved_chords" ? 7 : 3));
        CHECK(result.output.find("State: paused") == std::string::npos);
        CHECK(result.output.find("Save: OK") != std::string::npos);
        sh3::application::OptionsStore reload(files, files);
        CHECK(reload.load() == MemoryFiles::E::ok && !reload.current().tone_enabled);
        CHECK(s.pauses.back());
    } else {
        CHECK(false);
    }
}
} // namespace

int main(int argc, char **argv) {
    CHECK(argc == 2);
    const std::string scenario = argv[1];
    auto &s = ctr_test::sdk();
    if (scenario == "fail_citro3d") {
        failure(ctr_test::Failure::citro3d, "CITRO3D");
    } else if (scenario == "fail_citro2d") {
        failure(ctr_test::Failure::citro2d, "CITRO2D");
    } else if (scenario == "fail_target") {
        failure(ctr_test::Failure::target, "SCREEN_TARGET");
    } else if (scenario == "error_apt_exit") {
        failure(ctr_test::Failure::target, "SCREEN_TARGET", true);
    } else {
        if (scenario.rfind("lifecycle_", 0) == 0) {
            setup_lifecycle(scenario);
        } else if (scenario == "normal") {
            // A held produces no new edge. The second A edge resumes.
            s.keys = {0, KEY_A, 0, KEY_A, KEY_START};
        } else if (scenario == "start_priority") {
            s.keys = {KEY_A | KEY_X | KEY_Y | KEY_SELECT | KEY_START};
        } else if (scenario == "apt_exit") {
            s.keys.clear();
        } else if (scenario == "hook_exit") {
            s.keys = {0};
            s.exit_hook = true;
        } else if (scenario == "frame_rejected") {
            s.keys = {0, KEY_START};
            s.frame_allowed = false;
        } else if (scenario == "audio_unavailable") {
            s.keys = {0, KEY_START};
            s.audio_result = -1;
            s.audio_status = sh3::platform::ctr::ToneStatus::ndsp_init_failed;
        } else if (scenario == "audio_alloc_failure" || scenario == "audio_flush_failure") {
            s.keys = {0, KEY_START};
            s.audio_status = scenario == "audio_alloc_failure"
                                 ? sh3::platform::ctr::ToneStatus::pcm_alloc_failed
                                 : sh3::platform::ctr::ToneStatus::cache_flush_failed;
            s.audio_result = scenario == "audio_alloc_failure" ? 0 : -2;
        } else if (scenario == "audio_sleep_muted" || scenario == "audio_sleep_paused" ||
                   scenario == "audio_sleep_running") {
            files.record(MemoryFiles::Id::options_a, scenario != "audio_sleep_muted", 1);
            s.keys = {scenario == "audio_sleep_paused" ? KEY_A : 0, 0, 0, KEY_START};
            s.hooks = {APTHOOK_ONWAKEUP, APTHOOK_ONSLEEP, APTHOOK_ONWAKEUP};
        } else if (scenario == "options_toggle" || scenario == "options_failure") {
            s.keys = {KEY_X | KEY_A, 0, KEY_START};
            if (scenario == "options_failure") {
                files.write_error = MemoryFiles::E::no_space;
            }
        } else if (scenario == "options_restore") {
            files.record(MemoryFiles::Id::options_a, false, 1);
            s.keys = {KEY_Y | KEY_X | KEY_A, 0, KEY_START};
        } else if (scenario == "resources_page") {
            s.keys = {KEY_SELECT | KEY_A | KEY_X | KEY_Y, KEY_SELECT, KEY_START};
        } else if (scenario == "resources_failure") {
            s.keys = {KEY_SELECT, KEY_START};
            s.frame_allowed = false;
            ctr_test::resource_sdk().memory_result = -4;
            ctr_test::resource_sdk().cpu_result = -5;
        } else if (scenario == "resources_refresh" || scenario == "resources_sleep") {
            s.keys.assign(scenario == "resources_refresh" ? 182 : 183, 0);
            s.keys.front() = KEY_SELECT;
            s.keys.back() = KEY_START;
            if (scenario == "resources_sleep") {
                s.reset_metrics_loop = 182;
            }
        } else if (scenario == "fixture_invalid") {
            files.files[0].size = 8;
            s.keys = {0, KEY_START};
        } else {
            CHECK(false);
        }
        const auto result = run();
        CHECK(result.code == 0);
        CHECK(result.output.find("GRAPHICS_INIT_FAILED") == std::string::npos);
        check_success_cleanup();
        CHECK(s.initial_tone_paused ==
              (scenario == "options_restore" || scenario == "audio_sleep_muted" ||
               scenario == "lifecycle_home_muted"));
        CHECK(s.flushes == 0 && s.swaps == 0 && s.waits == 0);
        if (scenario.rfind("lifecycle_", 0) == 0) {
            check_lifecycle(scenario, result);
        } else if (scenario == "normal") {
            CHECK(s.scans == 5 && s.reads == 5 && s.begins == 4 && s.ends == 4);
            CHECK(ctr_test::resource_sdk().samples == 3); // Initial, paused, resumed epochs.
            CHECK(s.rectangles.size() == 8);
            CHECK(s.pauses == (std::vector<bool>{false, true, true, false}));
            check_frame(0, C2D_Color32(60, 200, 120, 255));
            check_frame(1, C2D_Color32(230, 160, 40, 255));
            check_frame(2, C2D_Color32(230, 160, 40, 255));
            check_frame(3, C2D_Color32(60, 200, 120, 255));
            CHECK(result.output.find("Build: host-contract") != std::string::npos);
            CHECK(result.output.find("State: paused") != std::string::npos);
            CHECK(result.output.find("State: running") != std::string::npos);
            CHECK(result.output.find("Audio: READY") != std::string::npos);
            CHECK(result.output.find("SDK frames: 123") != std::string::npos);
            CHECK(result.output.find("Pos: 456") != std::string::npos);
            CHECK(result.output.find("Listening: NOT_VERIFIED") != std::string::npos);
        } else if (scenario == "frame_rejected") {
            CHECK(s.begins == 1 && s.ends == 0 && s.rectangles.empty());
            CHECK(s.scans == 2 && s.reads == 2);
        } else if (scenario == "audio_unavailable") {
            CHECK(s.begins == 1 && s.ends == 1 && s.rectangles.size() == 2);
            CHECK(s.scans == 2 && s.reads == 2);
            CHECK(result.output.find("Audio: NDSP_INIT_FAILED") != std::string::npos);
            CHECK(result.output.find("Result: 0xffffffff") != std::string::npos);
            CHECK(result.output.find("Stage: NDSP_INIT") != std::string::npos);
        } else if (scenario == "audio_alloc_failure" || scenario == "audio_flush_failure") {
            const bool alloc = scenario == "audio_alloc_failure";
            CHECK(result.output.find(alloc ? "Audio: PCM_ALLOC_FAILED"
                                           : "Audio: CACHE_FLUSH_FAILED") != std::string::npos);
            CHECK(result.output.find(alloc ? "Result: N/A" : "Result: 0xfffffffe") !=
                  std::string::npos);
            CHECK(result.output.find("Scene: diagnostic") != std::string::npos);
            CHECK(result.output.find("Build: host-contract") != std::string::npos);
            CHECK(result.output.find("Channel: unavailable") != std::string::npos);
            CHECK(result.output.find("Audio: READY") == std::string::npos);
        } else if (scenario == "audio_sleep_muted" || scenario == "audio_sleep_paused" ||
                   scenario == "audio_sleep_running") {
            const bool remains_paused = scenario != "audio_sleep_running";
            CHECK(s.pauses == (std::vector<bool>{remains_paused, true, true, remains_paused}));
            CHECK(s.reads == 3 && s.begins == 2);
        } else if (scenario == "options_toggle" || scenario == "options_restore" ||
                   scenario == "options_failure") {
            CHECK(files.writes == 1 && s.begins == 2 && s.ends == 2);
            CHECK(result.output.find("State: paused") == std::string::npos);
            if (scenario == "options_failure") {
                CHECK(result.output.find("Save: NO_SPACE") != std::string::npos);
                CHECK(s.pauses == (std::vector<bool>{false, false}));
            } else {
                CHECK(result.output.find("Save: OK") != std::string::npos);
                CHECK(s.pauses == (std::vector<bool>{scenario == "options_toggle",
                                                     scenario == "options_toggle"}));
                sh3::application::OptionsStore reload(files, files);
                CHECK(reload.load() == MemoryFiles::E::ok);
                CHECK(reload.current().tone_enabled == (scenario == "options_restore"));
            }
        } else if (scenario == "resources_page") {
            CHECK(files.writes == 0 && s.begins == 2 && s.clears == 2);
            CHECK(ctr_test::resource_sdk().samples == 1);
            CHECK(result.output.find("B_app             UNKNOWN") != std::string::npos);
            CHECK(result.output.find("Heap capacity     64") != std::string::npos);
            CHECK(result.output.find("Launcher/version: UNKNOWN") != std::string::npos);
            CHECK(result.output.find("Audio: READY") != std::string::npos);
            CHECK(result.output.find("State: paused") == std::string::npos);
            const auto start = result.output.find("SH3 resources");
            const auto end = result.output.find("\x1b[1;1HSH3 synthetic", start);
            CHECK(start != std::string::npos && end != std::string::npos);
            const auto page = result.output.substr(start, end - start);
            std::size_t line = 0, rows = 1;
            for (const char ch : page) {
                if (ch == '\n') {
                    CHECK(line <= 39);
                    line = 0;
                    ++rows;
                } else {
                    ++line;
                }
            }
            CHECK(line <= 39 && rows <= 29);
        } else if (scenario == "resources_failure") {
            CHECK(files.writes == 0 && s.begins == 1 && s.ends == 0);
            CHECK(result.output.find("Region Result     0xfffffffc") != std::string::npos);
            CHECK(result.output.find("APT Result        0xfffffffb") != std::string::npos);
            CHECK(result.output.find("App region used   SDK_ERROR") != std::string::npos);
            CHECK(result.output.find("Rejected: 1") != std::string::npos);
        } else if (scenario == "resources_refresh" || scenario == "resources_sleep") {
            CHECK(files.writes == 0);
            CHECK(ctr_test::resource_sdk().samples == (scenario == "resources_sleep" ? 5 : 4));
            CHECK(result.output.find(" n: 120  unavailable: 0") != std::string::npos);
            CHECK(result.output.find("Draw+submit       10") != std::string::npos);
            if (scenario == "resources_sleep") {
                const auto last = result.output.substr(result.output.rfind("SH3 resources"));
                CHECK(last.find("warmup: 59") != std::string::npos);
                CHECK(last.find("Begin wait+SDK    UNKNOWN") != std::string::npos);
                CHECK(last.find(" n: 0    unavailable: 0") != std::string::npos);
            }
        } else if (scenario == "fixture_invalid") {
            CHECK(files.writes == 0 && s.begins == 1);
            CHECK(result.output.find("Probe: INVALID_DATA") != std::string::npos);
        } else {
            CHECK(files.writes == 0);
            CHECK(s.begins == 0 && s.ends == 0 && s.rectangles.empty());
            CHECK(s.pauses ==
                  (scenario == "hook_exit" ? std::vector<bool>{true} : std::vector<bool>{}));
            const unsigned expected_reads = scenario == "start_priority" ? 1 : 0;
            CHECK(s.scans == expected_reads && s.reads == expected_reads);
        }
    }
    std::printf("ctr_%s: adapter contract passed (SDK doubles)\n", argv[1]);
}
