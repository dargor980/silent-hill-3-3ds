#pragma once
extern "C" {
#include <libavcodec/avcodec.h>
#include <libavformat/avformat.h>
#include <libavutil/avutil.h>
#include <libavutil/channel_layout.h>
#include <libavutil/opt.h>
#include <libswresample/swresample.h>
#include <libswscale/swscale.h>
}
#include <array>
#include <cmath>
#include <cstdint>
#include <cstdio>
#include <cstring>
#include <filesystem>
#include <fstream>
#include <memory>
#include <stdexcept>
#include <string>
#include <vector>

inline void require(bool ok, const char *message)
{
    if (!ok) throw std::runtime_error(message);
}
inline void success(int code, const char *operation)
{
    if (code < 0) {
        char message[AV_ERROR_MAX_STRING_SIZE];
        av_strerror(code, message, sizeof(message));
        throw std::runtime_error(std::string(operation) + ": " + message);
    }
}
template<class T, void (*Release)(T **)>
struct ReleasePtr {
    void operator()(T *pointer) const { Release(&pointer); }
};
template<class T, void (*Release)(T **)>
using Owned = std::unique_ptr<T, ReleasePtr<T, Release>>;
using Frame = Owned<AVFrame, av_frame_free>;
using Packet = Owned<AVPacket, av_packet_free>;
using Codec = Owned<AVCodecContext, avcodec_free_context>;
using Resampler = Owned<SwrContext, swr_free>;
struct ReleaseFormat {
    void operator()(AVFormatContext *context) const
    {
        if (context->pb) avio_closep(&context->pb);
        avformat_free_context(context);
    }
};
using Format = std::unique_ptr<AVFormatContext, ReleaseFormat>;

inline Codec audioCodec(AVCodecID id)
{
    const auto *encoder = avcodec_find_encoder(id);
    require(encoder, "PCM encoder missing");
    Codec context(avcodec_alloc_context3(encoder));
    require(bool(context), "Audio context allocation failed");
    context->sample_rate = 48000;
    context->sample_fmt = AV_SAMPLE_FMT_S16;
    context->ch_layout = AV_CHANNEL_LAYOUT_STEREO;
    context->time_base = {1, 48000};
    success(avcodec_open2(context.get(), encoder, nullptr), "open PCM");
    return context;
}

inline constexpr std::array<int16_t, 16> pcmData{
    -32768, 32767, -16384, 16384, -1, 1, 0, 0,
    256, -256, 8192, -8192, 12345, -23456, 42, -42};

inline std::vector<uint8_t> pcmOracle(bool little)
{
    std::vector<uint8_t> bytes;
    for (const auto sample : pcmData) {
        const auto value = static_cast<uint16_t>(sample);
        bytes.push_back(static_cast<uint8_t>(little ? value : value >> 8));
        bytes.push_back(static_cast<uint8_t>(little ? value >> 8 : value));
    }
    return bytes;
}

inline Packet encodePCM(AVCodecContext *context)
{
    Frame frame(av_frame_alloc());
    Packet packet(av_packet_alloc());
    require(frame && packet, "Frame/packet allocation failed");
    frame->format = AV_SAMPLE_FMT_S16;
    frame->sample_rate = 48000;
    frame->nb_samples = static_cast<int>(pcmData.size() / 2);
    frame->pts = 0;
    success(av_channel_layout_copy(&frame->ch_layout, &context->ch_layout), "copy channels");
    success(av_frame_get_buffer(frame.get(), 0), "allocate audio buffer");
    std::memcpy(frame->data[0], pcmData.data(), sizeof(pcmData));
    success(avcodec_send_frame(context, frame.get()), "send PCM");
    success(avcodec_receive_packet(context, packet.get()), "receive PCM");
    require(packet->pts == 0 && packet->duration == 8, "PCM timestamps differ");
    return packet;
}
