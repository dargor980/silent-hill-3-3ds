// Own synthetic integration fixture. No physical device writes or game data.
#define SDL_MAIN_HANDLED
#include <SDL3/SDL.h>
#include <SDL3/SDL_main.h>

#include <array>
#include <cmath>
#include <cstring>
#include <iostream>
#include <memory>
#include <stdexcept>
#include <string>

namespace {
void require(bool condition, const char* operation) {
    if (!condition) {
        throw std::runtime_error(std::string(operation) + ": " + SDL_GetError());
    }
}

struct Session {
    explicit Session(SDL_InitFlags flags) { require(SDL_Init(flags), "SDL_Init"); }
    ~Session() { SDL_Quit(); }
    Session(const Session&) = delete;
    Session& operator=(const Session&) = delete;
};

struct VirtualDevice {
    SDL_JoystickID id;
    explicit VirtualDevice(const SDL_VirtualJoystickDesc& descriptor)
        : id(SDL_AttachVirtualJoystick(&descriptor)) {
        require(id != 0, "attach virtual joystick");
    }
    ~VirtualDevice() { if (id) SDL_DetachVirtualJoystick(id); }
    VirtualDevice(const VirtualDevice&) = delete;
    VirtualDevice& operator=(const VirtualDevice&) = delete;
};

void events() {
    require(SDL_RegisterEvents(0) == 0, "reject zero event allocation");
    const auto type = SDL_RegisterEvents(1);
    require(type != 0, "register event type");
    int token = 42;
    for (const int code : {17, -3}) {
        SDL_Event event{};
        event.type = type;
        event.user.code = code;
        event.user.data1 = &token;
        require(SDL_PushEvent(&event), "push event");
    }
    std::array<SDL_Event, 2> received{};
    require(SDL_PeepEvents(received.data(), 2, SDL_GETEVENT, type, type) == 2,
            "read exactly two own events");
    require(received[0].user.code == 17 && received[1].user.code == -3,
            "event FIFO order");
    for (const auto& event : received) {
        require(event.type == type && event.user.data1 == &token, "event content");
    }
    require(SDL_PeepEvents(received.data(), 2, SDL_GETEVENT, type, type) == 0,
            "own event queue drained");
}

void gamepad() {
    SDL_VirtualJoystickDesc descriptor{};
    SDL_INIT_INTERFACE(&descriptor);
    descriptor.type = SDL_JOYSTICK_TYPE_GAMEPAD;
    descriptor.naxes = 2;
    descriptor.nbuttons = 1;
    descriptor.axis_mask = (1u << SDL_GAMEPAD_AXIS_LEFTX) | (1u << SDL_GAMEPAD_AXIS_LEFTY);
    descriptor.button_mask = 1u << SDL_GAMEPAD_BUTTON_SOUTH;
    descriptor.name = "SH3 synthetic fixture";
    VirtualDevice device(descriptor);
    require(SDL_IsJoystickVirtual(device.id) && SDL_IsGamepad(device.id),
            "virtual gamepad identification");
    std::unique_ptr<SDL_Gamepad, decltype(&SDL_CloseGamepad)> pad(
        SDL_OpenGamepad(device.id), SDL_CloseGamepad);
    require(pad != nullptr, "open virtual gamepad");
    auto* joystick = SDL_GetGamepadJoystick(pad.get());
    require(joystick != nullptr, "gamepad joystick handle");
    for (const Sint16 value : {Sint16{-32768}, Sint16{0}, Sint16{32767}}) {
        require(SDL_SetJoystickVirtualAxis(joystick, 0, value), "set virtual axis");
        SDL_UpdateJoysticks();
        require(SDL_GetGamepadAxis(pad.get(), SDL_GAMEPAD_AXIS_LEFTX) == value,
                "axis endpoints and neutral");
    }
    for (const bool down : {true, false}) {
        require(SDL_SetJoystickVirtualButton(joystick, 0, down), "set virtual button");
        SDL_UpdateJoysticks();
        require(SDL_GetGamepadButton(pad.get(), SDL_GAMEPAD_BUTTON_SOUTH) == down,
                "button press and release");
    }
    require(!SDL_SetJoystickVirtualAxis(joystick, descriptor.naxes, 0),
            "reject out-of-range virtual axis");
    require(!SDL_SetJoystickVirtualButton(joystick, descriptor.nbuttons, true),
            "reject out-of-range virtual button");
    pad.reset();
    require(SDL_DetachVirtualJoystick(device.id), "detach virtual joystick");
    require(!SDL_IsJoystickVirtual(device.id), "virtual device removed");
    device.id = 0;
}

void audio() {
    const std::array<Sint16, 5> pcm{-32768, -16384, 0, 16384, 32767};
    const SDL_AudioSpec source{SDL_AUDIO_S16, 1, 48000};
    const SDL_AudioSpec destination{SDL_AUDIO_F32, 1, 48000};
    Uint8* raw = nullptr;
    int length = 0;
    require(SDL_ConvertAudioSamples(&source, reinterpret_cast<const Uint8*>(pcm.data()),
                sizeof(pcm), &destination, &raw, &length), "convert PCM to float");
    std::unique_ptr<Uint8, decltype(&SDL_free)> converted(raw, SDL_free);
    require(converted && length == static_cast<int>(pcm.size() * sizeof(float)),
            "converted sample count");
    for (std::size_t i = 0; i < pcm.size(); ++i) {
        float sample = 0;
        std::memcpy(&sample, converted.get() + i * sizeof(float), sizeof(float));
        require(std::abs(sample - static_cast<float>(pcm[i]) / 32768.0f) < 0.000001f,
                "PCM amplitude conversion");
    }
    const SDL_AudioSpec invalid{SDL_AUDIO_F32, 0, 48000};
    Uint8* invalid_output = nullptr;
    int invalid_length = 0;
    const bool accepted = SDL_ConvertAudioSamples(&source,
        reinterpret_cast<const Uint8*>(pcm.data()), sizeof(pcm), &invalid,
        &invalid_output, &invalid_length);
    std::unique_ptr<Uint8, decltype(&SDL_free)> invalid_result(invalid_output, SDL_free);
    require(!accepted && !invalid_result, "reject zero audio channels");
}

void memory() {
    const std::array<Uint8, 4> bytes{0, 17, 255, 42};
    std::unique_ptr<SDL_IOStream, decltype(&SDL_CloseIO)> stream(
        SDL_IOFromConstMem(bytes.data(), bytes.size()), SDL_CloseIO);
    require(stream != nullptr, "open memory stream");
    std::array<Uint8, 8> output{};
    output.fill(99);
    require(SDL_ReadIO(stream.get(), output.data(), output.size()) == bytes.size(),
            "bounded memory read");
    require(std::memcmp(output.data(), bytes.data(), bytes.size()) == 0,
            "memory stream content");
    for (std::size_t i = bytes.size(); i < output.size(); ++i) {
        require(output[i] == 99, "read leaves output tail unchanged");
    }
    require(SDL_ReadIO(stream.get(), output.data(), 1) == 0 &&
            SDL_GetIOStatus(stream.get()) == SDL_IO_STATUS_EOF, "memory EOF");
    require(SDL_SeekIO(stream.get(), 1, SDL_IO_SEEK_SET) == 1, "memory seek");
    require(SDL_ReadIO(stream.get(), output.data(), 2) == 2 &&
            output[0] == 17 && output[1] == 255, "read after seek");
    require(SDL_CloseIO(stream.release()), "close memory stream");
}
}  // namespace

int main(int argc, char** argv) {
    try {
        require(argc == 2, "expected test case argument");
        require(SDL_GetVersion() == SDL_VERSION, "header/library version match");
        SDL_SetMainReady();
        const std::string selected = argv[1];
        Session session(selected == "gamepad" ? SDL_INIT_GAMEPAD : SDL_INIT_EVENTS);
        if (selected == "events") events();
        else if (selected == "gamepad") gamepad();
        else if (selected == "audio") audio();
        else if (selected == "memory") memory();
        else require(false, "unknown test case");
        std::cout << selected << ": PASS\n";
    } catch (const std::exception& error) {
        std::cerr << error.what() << '\n';
        return 1;
    }
}
