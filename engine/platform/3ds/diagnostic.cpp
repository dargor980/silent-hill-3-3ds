#include "diagnostic.hpp"
#include "file_probe.hpp"
#include "resource_probe.hpp"
#include "sh3/application/diagnostic_app.hpp"
#include "sh3/platform/bounded_log.hpp"
#include "sh3/platform/stdio_files.hpp"
#include "sh3/platform/timing_window.hpp"
#include "tone.hpp"
#include <3ds.h>
#include <citro2d.h>
#include <cstdio>

namespace {
using E = sh3::domain::LifecycleEvent;
using S = sh3::domain::SessionState;

class Graphics final {
  public:
    Graphics() noexcept {
        gfxInitDefault();
        consoleInit(GFX_BOTTOM, nullptr);
        ready3d_ = C3D_Init(C3D_DEFAULT_CMDBUF_SIZE);
        if (!ready3d_) {
            failure_stage_ = "CITRO3D";
            return;
        }
        ready2d_ = C2D_Init(C2D_DEFAULT_MAX_OBJECTS);
        if (!ready2d_) {
            failure_stage_ = "CITRO2D";
            return;
        }
        C2D_Prepare();
        target_ = C2D_CreateScreenTarget(GFX_TOP, GFX_LEFT);
        if (target_ == nullptr) {
            failure_stage_ = "SCREEN_TARGET";
        }
    }
    ~Graphics() {
        if (target_ != nullptr) {
            // Deletion waits for queued GPU work before C2D frees its vertex buffers.
            C3D_RenderTargetDelete(target_);
        }
        if (ready2d_) {
            C2D_Fini();
        }
        if (ready3d_) {
            C3D_Fini();
        }
        gfxExit();
    }
    Graphics(const Graphics &) = delete;
    Graphics &operator=(const Graphics &) = delete;
    [[nodiscard]] C3D_RenderTarget *target() const noexcept { return target_; }
    [[nodiscard]] const char *failure_stage() const noexcept { return failure_stage_; }

  private:
    const char *failure_stage_{"NONE"};
    bool ready3d_{false};
    bool ready2d_{false};
    C3D_RenderTarget *target_{nullptr};
};

enum class OptionsAction { none, toggle, restore };

class Input final : public sh3::ports::IInputSource {
  public:
    void wait_for_release() noexcept {
        awaiting_release_ = true;
        action_ = OptionsAction::none;
    }
    E poll() noexcept override {
        action_ = OptionsAction::none;
        hidScanInput();
        const auto keys = hidKeysDown();
        const auto held = hidKeysHeld();
        if (awaiting_release_) {
            awaiting_release_ = (keys | held) != 0;
            return E::none;
        }
        constexpr u32 commands = KEY_A | KEY_START | KEY_SELECT | KEY_X | KEY_Y;
        if (((keys | held) & ~commands) != 0) {
            wait_for_release();
            return E::none;
        }
        if ((keys & KEY_START) != 0) {
            return E::quit;
        }
        if ((keys & KEY_SELECT) != 0) {
            resources_ = !resources_;
            return E::none;
        }
        if ((keys & KEY_Y) != 0) {
            action_ = OptionsAction::restore;
            return E::none;
        }
        if ((keys & KEY_X) != 0) {
            action_ = OptionsAction::toggle;
            return E::none;
        }
        return (keys & KEY_A) != 0 ? E::toggle_pause : E::none;
    }
    [[nodiscard]] OptionsAction options_action() const noexcept { return action_; }
    [[nodiscard]] bool resources_visible() const noexcept { return resources_; }
    [[nodiscard]] bool awaiting_release() const noexcept { return awaiting_release_; }

  private:
    OptionsAction action_{OptionsAction::none};
    bool resources_{false};
    bool awaiting_release_{false};
};

class View final : public sh3::ports::IDiagnosticView {
  public:
    View(C3D_RenderTarget &target, const sh3::platform::ctr::Tone &tone,
         const sh3::platform::ctr::FileProbe &files, const Input &input) noexcept
        : target_(target), tone_(tone), files_(files), input_(input) {}
    void restart_metrics() noexcept {
        timings_.reset();
        refresh_countdown_ = 0;
    }
    void present(S state) noexcept override {
        if (state != last_state_) {
            restart_metrics();
            last_state_ = state;
        }
        const bool refresh = refresh_countdown_ == 0;
        if (refresh) {
            resources_ = probe_.sample();
            refresh_countdown_ = 60;
        }
        --refresh_countdown_;
        const auto begin = svcGetSystemTick();
        const bool accepted = C3D_FrameBegin(C3D_FRAME_SYNCDRAW);
        const auto after_wait = svcGetSystemTick();
        sh3::platform::FrameTimings sample;
        sample.accepted = accepted;
        sample.begin_wait = sh3::platform::elapsed_ticks(begin, after_wait);
        if (!accepted) {
            timings_.record(sample);
            update_summary(refresh);
            show_page(state);
            return;
        }
        C2D_TargetClear(&target_, C2D_Color32(20, 22, 28, 255));
        C2D_SceneBegin(&target_);
        const auto color =
            state == S::paused ? C2D_Color32(230, 160, 40, 255) : C2D_Color32(60, 200, 120, 255);
        C2D_DrawRectSolid(40.0F, 40.0F, 0.0F, 320.0F, 160.0F, color);
        C2D_DrawRectSolid(80.0F, 80.0F, 0.0F, 80.0F, 80.0F, C2D_Color32(30, 30, 40, 255));
        C3D_FrameEnd(0);
        const auto after_submit = svcGetSystemTick();
        const auto audio = tone_.snapshot();
        const auto after_audio = svcGetSystemTick();
        sample.draw_submit = sh3::platform::elapsed_ticks(after_wait, after_submit);
        sample.audio_poll = sh3::platform::elapsed_ticks(after_submit, after_audio);
        timings_.record(sample);
        update_summary(refresh);
        if (show_page(state)) {
            return;
        }
        const bool audio_ready = audio.status == sh3::platform::ctr::ToneStatus::ready;
        char result[11]{};
        if (audio.status == sh3::platform::ctr::ToneStatus::pcm_alloc_failed) {
            std::snprintf(result, sizeof(result), "N/A");
        } else {
            std::snprintf(result, sizeof(result), "0x%08lx",
                          static_cast<unsigned long>(static_cast<u32>(audio.sdk_result)));
        }
        std::printf("\x1b[1;1HSH3 synthetic diagnostic\nBuild: %s\n"
                    "%-38s\nState: %-8s\n"
                    "Scene: diagnostic\nAudio: %-18s\nStage: %-11s Result: %-10s\n"
                    "SDK frames: %-10lu\nDropped: %-10lu Pos: %-10lu\n"
                    "Channel: %-11s\nListening: NOT_VERIFIED\n"
                    "X: tone+save  Y: defaults+save\nTone: %-3s\n"
                    "Probe: %-20s\nLoad: %-20s\nSave: %-20s\n"
                    "SELECT: resources (synthetic only)\n",
                    SH3_BUILD_ID,
                    input_.awaiting_release() ? "Release all buttons to enable controls"
                                              : "A: pause/resume  START: exit",
                    state == S::paused ? "paused" : "running",
                    sh3::platform::ctr::tone_status_name(audio.status),
                    sh3::platform::ctr::tone_stage_name(audio.status), result,
                    static_cast<unsigned long>(audio.frames),
                    static_cast<unsigned long>(audio.dropped_frames),
                    static_cast<unsigned long>(audio.sample_position),
                    audio_ready ? (audio.paused ? "paused" : "unpaused") : "unavailable",
                    files_.tone_enabled() ? "on" : "off",
                    sh3::platform::file_error_name(files_.fixture_status()),
                    sh3::platform::file_error_name(files_.load_status()),
                    files_.save_attempted() ? sh3::platform::file_error_name(files_.save_status())
                                            : "NOT_RUN");
    }

  private:
    void update_summary(bool refresh) noexcept {
        if (refresh) {
            summaries_[0] = timings_.summarize(&sh3::platform::FrameTimings::begin_wait);
            summaries_[1] = timings_.summarize(&sh3::platform::FrameTimings::draw_submit);
            summaries_[2] = timings_.summarize(&sh3::platform::FrameTimings::audio_poll);
            warmup_ = timings_.warmup_remaining();
            rejected_ = timings_.rejected();
        }
    }
    static void reading(const char *label,
                        const sh3::platform::ctr::ResourceReading &item) noexcept {
        char value[21]{};
        sh3::platform::ctr::format_reading(item, value);
        std::printf("%-17s %-20s\n", label, value);
    }
    static void result(const char *label, std::int32_t code) noexcept {
        std::printf("%-17s 0x%08lx          \n", label,
                    static_cast<unsigned long>(static_cast<u32>(code)));
    }
    bool show_page(S state) noexcept {
        const bool resources_visible = input_.resources_visible();
        if (resources_visible != previous_page_) {
            consoleClear();
            previous_page_ = resources_visible;
        }
        if (!resources_visible) {
            return false;
        }
        std::printf("\x1b[1;1HSH3 resources (bytes, no pool sum)\nBuild: %s\n"
                    "%-38s\nState: %-8s  Env HB: %s\n",
                    SH3_BUILD_ID,
                    input_.awaiting_release() ? "Release all buttons to enable controls"
                                              : "SELECT: audio/files  START: exit",
                    state == S::paused ? "paused" : "running", resources_.homebrew ? "yes" : "no ");
        reading("New family (0/1)", resources_.new_family);
        result("Family Result", resources_.new_family.result);
        std::printf("Launcher/version: UNKNOWN\n");
        reading("CPU clock Hz", resources_.cpu_clock_hz);
        reading("APT CPU limit %", resources_.apt_cpu_limit_percent);
        result("APT Result", resources_.apt_cpu_limit_percent.result);
        reading("B_app", resources_.app_budget);
        reading("Heap capacity", resources_.heap_capacity);
        reading("Heap free", resources_.heap_free);
        reading("Linear capacity", resources_.linear_capacity);
        reading("Linear free", resources_.linear_free);
        reading("VRAM free", resources_.vram_free);
        reading("App region cap", resources_.app_region_capacity);
        reading("App region used", resources_.app_region_used);
        result("Region Result", resources_.app_region_used.result);
        std::printf("Rolling ticks p95; warmup: %-2lu\n", static_cast<unsigned long>(warmup_));
        constexpr const char *names[]{"Begin wait+SDK", "Draw+submit", "Audio poll"};
        for (std::size_t i = 0; i < summaries_.size(); ++i) {
            const auto &summary = summaries_[i];
            reading(names[i], {summary.p95 ? sh3::platform::ctr::ReadingStatus::available
                                           : sh3::platform::ctr::ReadingStatus::unmeasured,
                               summary.p95.value_or(0), 0});
            std::printf(" n: %-3lu  unavailable: %-3lu         \n",
                        static_cast<unsigned long>(summary.valid),
                        static_cast<unsigned long>(summary.invalid));
        }
        std::printf("Rejected: %-20llu\nSim/anim/load/GPU: UNMEASURED\n"
                    "No game benchmark.",
                    static_cast<unsigned long long>(rejected_));
        return true;
    }
    C3D_RenderTarget &target_;
    const sh3::platform::ctr::Tone &tone_;
    const sh3::platform::ctr::FileProbe &files_;
    const Input &input_;
    sh3::platform::ctr::ResourceProbe probe_;
    sh3::platform::ctr::ResourceSnapshot resources_;
    sh3::platform::TimingWindow timings_;
    std::array<sh3::platform::TimingSummary, 3> summaries_{};
    std::size_t warmup_{sh3::platform::TimingWindow::warmup_attempts};
    std::uint64_t rejected_{0};
    unsigned refresh_countdown_{0};
    S last_state_{S::running};
    bool previous_page_{false};
};

class LifecycleHook final {
  public:
    LifecycleHook(sh3::application::DiagnosticApp &app, sh3::platform::ctr::Tone &tone, View &view,
                  Input &input) noexcept
        : app_(app), tone_(tone), view_(view), input_(input) {
        aptHook(&cookie_, callback, this);
    }
    ~LifecycleHook() { aptUnhook(&cookie_); }
    LifecycleHook(const LifecycleHook &) = delete;
    LifecycleHook &operator=(const LifecycleHook &) = delete;

  private:
    static void callback(APT_HookType hook, void *context) {
        auto &self = *static_cast<LifecycleHook *>(context);
        const auto before = self.app_.state();
        if (before == S::stopped) {
            return;
        }
        if (hook == APTHOOK_ONSUSPEND || hook == APTHOOK_ONSLEEP) {
            self.app_.dispatch(E::suspend);
        } else if (hook == APTHOOK_ONRESTORE || hook == APTHOOK_ONWAKEUP) {
            self.app_.dispatch(E::resume);
        } else if (hook == APTHOOK_ONEXIT) {
            self.app_.dispatch(E::quit);
        }
        const auto after = self.app_.state();
        if (before == after) {
            return;
        }
        if (after == S::suspended) {
            self.view_.restart_metrics();
            self.tone_.pause(true);
        } else if (after == S::stopped) {
            self.tone_.pause(true);
        } else if (before == S::suspended) {
            self.view_.restart_metrics();
            self.input_.wait_for_release();
        }
    }
    aptHookCookie cookie_{};
    sh3::application::DiagnosticApp &app_;
    sh3::platform::ctr::Tone &tone_;
    View &view_;
    Input &input_;
};
} // namespace

int sh3::platform::ctr::run_diagnostic(ports::IFileReader &reader, ports::IFileWriter &writer) {
    Graphics graphics;
    if (graphics.target() == nullptr) {
        std::printf("GRAPHICS_INIT_FAILED\nStage: %s\nBuild: %s\nSTART to exit\n",
                    graphics.failure_stage(), SH3_BUILD_ID);
        Input input;
        while (aptMainLoop()) {
            if (input.poll() == E::quit) {
                break;
            }
            gfxFlushBuffers();
            gfxSwapBuffers();
            gspWaitForVBlank();
        }
        return 1;
    }
    FileProbe files(reader, writer);
    sh3::platform::ctr::Tone tone(!files.tone_enabled());
    Input input;
    View view(*graphics.target(), tone, files, input);
    sh3::platform::BoundedLog log;
    sh3::application::DiagnosticApp app(input, view, log);
    LifecycleHook hook(app, tone, view, input);
    while (aptMainLoop() && app.step()) {
        if (app.state() != S::suspended) {
            if (input.options_action() == OptionsAction::restore) {
                files.restore_defaults();
            } else if (input.options_action() == OptionsAction::toggle) {
                files.toggle_tone();
            }
        }
        tone.pause(app.state() != S::running || !files.tone_enabled());
    }
    app.dispatch(E::quit);
    return 0;
}
