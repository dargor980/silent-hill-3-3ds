#include "tone.hpp"
#include <cmath>
#include <cstdint>

namespace sh3::platform::ctr {
Tone::Tone(bool paused) noexcept {
    result_ = ndspInit();
    if (R_FAILED(result_)) {
        return;
    }
    initialized_ = true;
    constexpr std::size_t count = 22050;
    samples_ = static_cast<std::int16_t *>(linearAlloc(count * sizeof(std::int16_t)));
    if (samples_ == nullptr) {
        status_ = ToneStatus::pcm_alloc_failed;
        release();
        return;
    }
    for (std::size_t i = 0; i < count; ++i) {
        samples_[i] = static_cast<std::int16_t>(
            2048.0 * std::sin(6.28318530718 * 440.0 * static_cast<double>(i) / 22050.0));
    }
    result_ = DSP_FlushDataCache(samples_, count * sizeof(std::int16_t));
    if (R_FAILED(result_)) {
        status_ = ToneStatus::cache_flush_failed;
        release();
        return;
    }
    ndspSetOutputMode(NDSP_OUTPUT_STEREO);
    ndspChnReset(0);
    ndspChnSetInterp(0, NDSP_INTERP_LINEAR);
    ndspChnSetRate(0, 22050.0F);
    ndspChnSetFormat(0, NDSP_FORMAT_MONO_PCM16);
    float mix[12]{};
    mix[0] = mix[1] = 0.5F;
    ndspChnSetMix(0, mix);
    wave_.data_vaddr = samples_;
    wave_.nsamples = count;
    wave_.looping = true;
    ndspChnSetPaused(0, paused);
    ndspChnWaveBufAdd(0, &wave_);
    queued_ = true;
    paused_ = paused;
    status_ = ToneStatus::ready;
}

Tone::~Tone() { release(); }

void Tone::release() noexcept {
    if (initialized_) {
        if (queued_) {
            ndspChnWaveBufClear(0);
            queued_ = false;
        }
        // Clearing the queue alone does not synchronize DSP memory access.
        // Keep the descriptor and PCM alive until the sole NDSP owner exits.
        ndspExit();
        initialized_ = false;
    }
    if (samples_ != nullptr) {
        linearFree(samples_);
        samples_ = nullptr;
    }
}

ToneSnapshot Tone::snapshot() const noexcept {
    ToneSnapshot value{status_, result_};
    if (status_ == ToneStatus::ready) {
        value.frames = ndspGetFrameCount();
        value.dropped_frames = ndspGetDroppedFrames();
        value.sample_position = ndspChnGetSamplePos(0);
        value.paused = paused_;
    }
    return value;
}
void Tone::pause(bool paused) noexcept {
    if (status_ == ToneStatus::ready && paused_ != paused) {
        ndspChnSetPaused(0, paused);
        paused_ = paused;
    }
}
} // namespace sh3::platform::ctr
