#include "audio_sdk.hpp"
#include "check.hpp"
#include <cstdlib>

namespace {
audio_test::Sdk state;
void channel(int id) { CHECK(state.initialized && state.configured && id == 0); }
} // namespace

namespace audio_test {
Sdk &sdk() { return state; }
} // namespace audio_test

Result ndspInit() {
    CHECK(!state.initialized);
    state.events.emplace_back("init");
    state.initialized = !R_FAILED(state.init_result);
    return state.init_result;
}
void ndspExit() {
    CHECK(state.initialized && !state.queued);
    if (state.wave) {
        // Descriptor and sample memory must still be accessible at the join boundary.
        CHECK(state.wave->data_vaddr == state.memory && state.wave->nsamples == 22050);
        CHECK(static_cast<const std::int16_t *>(state.memory)[100] != 0);
    }
    state.initialized = state.configured = false;
    state.wave = nullptr;
    state.events.emplace_back("exit");
}
void *linearAlloc(std::size_t size) {
    CHECK(state.initialized && !state.memory && size == 44100);
    state.bytes = size;
    state.events.emplace_back("alloc");
    state.memory = state.allocation_fails ? nullptr : std::malloc(size);
    CHECK(state.allocation_fails || state.memory);
    return state.memory;
}
void linearFree(void *memory) {
    CHECK(!state.initialized && !state.queued && memory && memory == state.memory);
    std::free(memory);
    state.memory = nullptr;
    state.events.emplace_back("free");
}
Result DSP_FlushDataCache(const void *address, u32 size) {
    CHECK(state.initialized && !state.configured && address == state.memory && size == state.bytes);
    state.events.emplace_back("flush");
    state.flushed = !R_FAILED(state.flush_result);
    return state.flush_result;
}
void ndspSetOutputMode(ndspOutputMode mode) {
    CHECK(state.initialized && state.flushed && mode == NDSP_OUTPUT_STEREO);
    state.configured = true;
    state.events.emplace_back("output");
}
void ndspChnReset(int id) {
    channel(id);
    CHECK(!state.queued);
    state.events.emplace_back("reset");
}
void ndspChnSetInterp(int id, ndspInterpType type) {
    channel(id);
    CHECK(type == NDSP_INTERP_LINEAR);
    state.events.emplace_back("interp");
}
void ndspChnSetRate(int id, float rate) {
    channel(id);
    CHECK(rate == 22050.0F);
    state.events.emplace_back("rate");
}
void ndspChnSetFormat(int id, u16 format) {
    channel(id);
    CHECK(format == NDSP_FORMAT_MONO_PCM16);
    state.events.emplace_back("format");
}
void ndspChnSetMix(int id, float mix[12]) {
    channel(id);
    CHECK(mix[0] == 0.5F && mix[1] == 0.5F);
    for (int i = 2; i < 12; ++i) {
        CHECK(mix[i] == 0.0F);
    }
    state.events.emplace_back("mix");
}
void ndspChnSetPaused(int id, bool paused) {
    channel(id);
    state.paused = paused;
    state.pause_set = true;
    state.pauses.push_back(paused);
    state.events.emplace_back("pause");
}
void ndspChnWaveBufAdd(int id, ndspWaveBuf *buffer) {
    channel(id);
    CHECK(state.flushed && state.pause_set && !state.queued && !state.wave);
    CHECK(buffer && buffer->data_vaddr == state.memory && buffer->nsamples == 22050);
    CHECK(buffer->looping);
    state.wave = buffer;
    state.queued = true;
    state.events.emplace_back("add");
}
void ndspChnWaveBufClear(int id) {
    channel(id);
    CHECK(state.queued && state.wave && state.memory);
    state.queued = false;
    state.events.emplace_back("clear");
}
u32 ndspGetFrameCount() {
    CHECK(state.initialized && state.queued);
    ++state.queries;
    return state.frames;
}
u32 ndspGetDroppedFrames() {
    CHECK(state.initialized && state.queued);
    ++state.queries;
    return state.dropped;
}
u32 ndspChnGetSamplePos(int id) {
    channel(id);
    CHECK(state.queued);
    ++state.queries;
    return state.position;
}
