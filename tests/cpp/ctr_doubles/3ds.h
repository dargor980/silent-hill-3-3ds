#pragma once

// Test-owned declarations of the SDK surface consumed by diagnostic.cpp.
// These are behavior doubles, not an emulator or an ABI-compatible SDK.
#include <cstddef>
#include <cstdint>

using u8 = std::uint8_t;
using u16 = std::uint16_t;
using u32 = std::uint32_t;
using u64 = std::uint64_t;
using s32 = std::int32_t;
using s64 = std::int64_t;
using Result = std::int32_t;
enum gfxScreen_t { GFX_TOP, GFX_BOTTOM };
enum gfx3dSide_t { GFX_LEFT, GFX_RIGHT };
inline constexpr u32 KEY_A = 1U;
inline constexpr u32 KEY_SELECT = 4U;
inline constexpr u32 KEY_START = 8U;
inline constexpr u32 KEY_X = 1U << 10;
inline constexpr u32 KEY_Y = 1U << 11;
inline constexpr u32 KEY_DOWN = 1U << 7;
inline constexpr u32 KEY_R = 1U << 8;
inline constexpr u32 KEY_L = 1U << 9;
struct PrintConsole {};
struct ndspWaveBuf {
    const void *data_vaddr{};
    u32 nsamples{};
    bool looping{};
};
inline constexpr bool R_FAILED(Result result) { return result < 0; }
enum ndspOutputMode { NDSP_OUTPUT_STEREO = 1 };
enum ndspInterpType { NDSP_INTERP_LINEAR = 1 };
inline constexpr u16 NDSP_FORMAT_MONO_PCM16 = 5;
Result ndspInit();
void ndspExit();
void *linearAlloc(std::size_t size);
void linearFree(void *memory);
Result DSP_FlushDataCache(const void *address, u32 size);
void ndspSetOutputMode(ndspOutputMode mode);
void ndspChnReset(int id);
void ndspChnSetInterp(int id, ndspInterpType type);
void ndspChnSetRate(int id, float rate);
void ndspChnSetFormat(int id, u16 format);
void ndspChnSetMix(int id, float mix[12]);
void ndspChnSetPaused(int id, bool paused);
void ndspChnWaveBufAdd(int id, ndspWaveBuf *buffer);
void ndspChnWaveBufClear(int id);
u32 ndspGetFrameCount();
u32 ndspGetDroppedFrames();
u32 ndspChnGetSamplePos(int id);
enum APT_HookType {
    APTHOOK_ONSUSPEND,
    APTHOOK_ONRESTORE,
    APTHOOK_ONSLEEP,
    APTHOOK_ONWAKEUP,
    APTHOOK_ONEXIT
};
struct aptHookCookie {};
using aptHookFn = void (*)(APT_HookType, void *);

void gfxInitDefault();
void gfxExit();
PrintConsole *consoleInit(gfxScreen_t screen, PrintConsole *console);
void consoleClear();
void gfxFlushBuffers();
void gfxSwapBuffers();
void gspWaitForVBlank();
void hidScanInput();
u32 hidKeysDown();
u32 hidKeysHeld();
bool aptMainLoop();
void aptHook(aptHookCookie *cookie, aptHookFn callback, void *context);
void aptUnhook(aptHookCookie *cookie);

enum MemRegion { MEMREGION_APPLICATION = 1 };
bool envIsHomebrew();
u32 envGetHeapSize();
u32 envGetLinearHeapSize();
u32 linearSpaceFree();
u32 vramSpaceFree();
u32 osGetMemRegionSize(MemRegion region);
Result svcGetSystemInfo(s64 *out, u32 type, s32 param);
Result APT_CheckNew3DS(bool *out);
Result APT_GetAppCpuTimeLimit(u32 *out);
u64 svcGetSystemTick();
