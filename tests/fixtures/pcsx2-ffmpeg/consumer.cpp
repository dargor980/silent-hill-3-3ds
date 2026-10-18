#include "fixture.hpp"

void profile()
{
    require(std::string(av_version_info()) == "8.1", "Unexpected FFmpeg release");
    require(avcodec_version() == LIBAVCODEC_VERSION_INT &&
                avformat_version() == LIBAVFORMAT_VERSION_INT &&
                avutil_version() == LIBAVUTIL_VERSION_INT &&
                swscale_version() == LIBSWSCALE_VERSION_INT &&
                swresample_version() == LIBSWRESAMPLE_VERSION_INT,
            "Headers and runtime versions differ");
    require(!avcodec_find_decoder(AV_CODEC_ID_FFV1), "Decoder unexpectedly enabled");
    require(!av_find_input_format("wav"), "Demuxer unexpectedly enabled");
    void *codecCursor = nullptr;
    int encoders = 0, decoders = 0;
    while (const auto *codec = av_codec_iterate(&codecCursor)) {
        encoders += av_codec_is_encoder(codec);
        decoders += av_codec_is_decoder(codec);
    }
    require(encoders == 12 && decoders == 0, "Unexpected runtime codec inventory");
    for (const auto *name : {"ffv1", "qtrle", "pcm_s16le", "pcm_s16be"})
        require(avcodec_find_encoder_by_name(name), "Required software encoder missing");
    for (const auto *name : {"avi", "matroska", "mov", "mp3", "mp4", "wav"})
        require(av_guess_format(name, nullptr, nullptr), "Required muxer missing");
    void *opaque = nullptr;
    const char *protocol = avio_enum_protocols(&opaque, 1);
    require(protocol && std::string(protocol) == "file" &&
                !avio_enum_protocols(&opaque, 1), "Unexpected output protocols");
}

void pcm()
{
    for (const bool little : {true, false}) {
        auto context = audioCodec(little ? AV_CODEC_ID_PCM_S16LE : AV_CODEC_ID_PCM_S16BE);
        auto packet = encodePCM(context.get());
        require(std::vector<uint8_t>(packet->data, packet->data + packet->size) == pcmOracle(little),
                "PCM encoded bytes differ");
        success(avcodec_send_frame(context.get(), nullptr), "drain PCM");
        require(avcodec_receive_packet(context.get(), packet.get()) == AVERROR_EOF, "PCM drain did not finish");
        require(avcodec_send_frame(context.get(), nullptr) == AVERROR_EOF, "Drained encoder accepted another drain");
    }
}

std::vector<std::vector<uint8_t>> encodeVideo(AVCodecID id)
{
    const auto *encoder = avcodec_find_encoder(id);
    require(encoder, "Video encoder missing");
    Codec context(avcodec_alloc_context3(encoder));
    Frame frame(av_frame_alloc());
    Packet packet(av_packet_alloc());
    require(context && frame && packet, "Video allocation failed");
    context->width = 32; context->height = 32;
    context->pix_fmt = id == AV_CODEC_ID_QTRLE ? AV_PIX_FMT_RGB24 : AV_PIX_FMT_YUV420P;
    context->time_base = {1, 25}; context->framerate = {25, 1};
    context->thread_count = 1; context->flags |= AV_CODEC_FLAG_BITEXACT;
    success(avcodec_open2(context.get(), encoder, nullptr), "open video");
    frame->format = context->pix_fmt; frame->width = 32; frame->height = 32;
    success(av_frame_get_buffer(frame.get(), 32), "allocate video buffer");
    std::vector<std::vector<uint8_t>> packets;
    auto receive = [&](bool final) {
        while (true) {
            const int result = avcodec_receive_packet(context.get(), packet.get());
            if (result == (final ? AVERROR_EOF : AVERROR(EAGAIN))) return;
            success(result, "receive video");
            require(packet->size > 0 && packet->pts == static_cast<int64_t>(packets.size()),
                    "Unexpected video packet/PTS");
            if (packets.empty()) require(packet->flags & AV_PKT_FLAG_KEY, "First video packet is not a keyframe");
            packets.emplace_back(packet->data, packet->data + packet->size);
            av_packet_unref(packet.get());
        }
    };
    for (int number = 0; number < 3; ++number) {
        success(av_frame_make_writable(frame.get()), "reuse video buffer");
        for (int plane = 0; plane < (id == AV_CODEC_ID_QTRLE ? 1 : 3); ++plane) {
            const int height = plane ? 16 : 32;
            const int width = id == AV_CODEC_ID_QTRLE ? 96 : (plane ? 16 : 32);
            for (int y = 0; y < height; ++y)
                for (int x = 0; x < width; ++x)
                    frame->data[plane][y * frame->linesize[plane] + x] =
                        static_cast<uint8_t>((x * 3 + y * 5 + number * 17 + plane * 64) & 255);
        }
        frame->pts = number;
        success(avcodec_send_frame(context.get(), frame.get()), "send video");
        receive(false);
    }
    success(avcodec_send_frame(context.get(), nullptr), "drain video");
    receive(true);
    require(packets.size() == 3, "Video frame count differs");
    require(avcodec_send_frame(context.get(), frame.get()) == AVERROR_EOF, "Drained encoder accepted a frame");
    return packets;
}

void video()
{
    for (const auto id : {AV_CODEC_ID_FFV1, AV_CODEC_ID_QTRLE}) {
        const auto first = encodeVideo(id);
        require(first == encodeVideo(id), "Video output is not repeatable");
        require(first[0] != first[1], "Different frames produced identical packets");
    }
}

uint32_t readLE(const std::vector<uint8_t> &bytes, size_t offset, unsigned size)
{
    require(offset + size <= bytes.size(), "Truncated RIFF field");
    uint32_t value = 0;
    for (unsigned i = 0; i < size; ++i) value |= uint32_t(bytes[offset + i]) << (8 * i);
    return value;
}

void wav(const std::filesystem::path &directory)
{
    const auto path = directory / "synthetic.wav";
    auto codec = audioCodec(AV_CODEC_ID_PCM_S16LE);
    AVFormatContext *raw = nullptr;
    success(avformat_alloc_output_context2(&raw, nullptr, "wav", path.c_str()), "allocate WAV");
    Format format(raw); require(bool(format), "WAV context missing");
    auto *stream = avformat_new_stream(format.get(), nullptr);
    require(stream, "WAV stream missing");
    success(avcodec_parameters_from_context(stream->codecpar, codec.get()), "copy PCM parameters");
    stream->time_base = codec->time_base;
    success(avio_open(&format->pb, path.c_str(), AVIO_FLAG_WRITE), "open WAV file");
    success(avformat_write_header(format.get(), nullptr), "write WAV header");
    auto packet = encodePCM(codec.get());
    av_packet_rescale_ts(packet.get(), codec->time_base, stream->time_base);
    packet->stream_index = stream->index;
    success(av_interleaved_write_frame(format.get(), packet.get()), "mux PCM packet");
    success(av_write_trailer(format.get()), "write WAV trailer");
    success(avio_closep(&format->pb), "close WAV");
    std::ifstream file(path, std::ios::binary);
    const std::vector<uint8_t> bytes((std::istreambuf_iterator<char>(file)), {});
    require(bytes.size() >= 12 && !std::memcmp(bytes.data(), "RIFF", 4) &&
                !std::memcmp(bytes.data() + 8, "WAVE", 4), "WAV signature differs");
    require(readLE(bytes, 4, 4) + 8 == bytes.size(), "RIFF length differs");
    bool foundFormat = false, foundData = false;
    for (size_t at = 12; at + 8 <= bytes.size();) {
        const size_t length = readLE(bytes, at + 4, 4);
        const size_t data = at + 8;
        require(length <= bytes.size() - data, "RIFF chunk outside file");
        if (!std::memcmp(bytes.data() + at, "fmt ", 4)) {
            require(length >= 16 && readLE(bytes, data, 2) == 1 &&
                        readLE(bytes, data + 2, 2) == 2 && readLE(bytes, data + 4, 4) == 48000 &&
                        readLE(bytes, data + 8, 4) == 192000 && readLE(bytes, data + 12, 2) == 4 &&
                        readLE(bytes, data + 14, 2) == 16, "WAV PCM metadata differs");
            foundFormat = true;
        } else if (!std::memcmp(bytes.data() + at, "data", 4)) {
            require(std::vector<uint8_t>(bytes.begin() + data, bytes.begin() + data + length) == pcmOracle(true),
                    "WAV payload differs from independent PCM oracle");
            foundData = true;
        }
        at = data + length + (length & 1);
    }
    require(foundFormat && foundData, "WAV chunks missing");
}

void scale()
{
    std::array<uint8_t, 4 * 4 * 3 + 64> input{};
    std::array<uint8_t, 8 * 8 * 4 + 64> output{};
    for (int i = 0; i < 16; ++i) {
        input[i * 3] = static_cast<uint8_t>(i * 13);
        input[i * 3 + 1] = static_cast<uint8_t>(255 - i * 11);
        input[i * 3 + 2] = static_cast<uint8_t>(i * 7);
    }
    std::unique_ptr<SwsContext, decltype(&sws_freeContext)> context(
        sws_getContext(4, 4, AV_PIX_FMT_RGB24, 8, 8, AV_PIX_FMT_BGRA, SWS_POINT, nullptr, nullptr, nullptr),
        &sws_freeContext);
    require(bool(context), "Scaler context missing");
    const uint8_t *sources[]{input.data(), nullptr, nullptr, nullptr};
    uint8_t *destinations[]{output.data(), nullptr, nullptr, nullptr};
    const int sourceStride[]{12, 0, 0, 0}, destinationStride[]{32, 0, 0, 0};
    require(sws_scale(context.get(), sources, sourceStride, 0, 4, destinations, destinationStride) == 8,
            "Scaler row count differs");
    for (int y = 0; y < 8; ++y)
        for (int x = 0; x < 8; ++x) {
            const int src = ((y / 2) * 4 + x / 2) * 3, dst = (y * 8 + x) * 4;
            require(output[dst] == input[src + 2] && output[dst + 1] == input[src + 1] &&
                        output[dst + 2] == input[src] && output[dst + 3] == 255, "Scaled pixel differs");
        }
}

void resample()
{
    AVChannelLayout stereo = AV_CHANNEL_LAYOUT_STEREO, mono = AV_CHANNEL_LAYOUT_MONO;
    SwrContext *raw = nullptr;
    success(swr_alloc_set_opts2(&raw, &stereo, AV_SAMPLE_FMT_FLTP, 48000,
                              &stereo, AV_SAMPLE_FMT_S16, 48000, 0, nullptr), "allocate format converter");
    Resampler convert(raw); success(swr_init(convert.get()), "init format converter");
    std::array<float, 8> left{}, right{};
    const uint8_t *input[]{reinterpret_cast<const uint8_t *>(pcmData.data())};
    uint8_t *output[]{reinterpret_cast<uint8_t *>(left.data()), reinterpret_cast<uint8_t *>(right.data())};
    require(swr_convert(convert.get(), output, 8, input, 8) == 8, "Sample conversion count differs");
    for (size_t i = 0; i < 8; ++i)
        require(left[i] == pcmData[i * 2] / 32768.0f && right[i] == pcmData[i * 2 + 1] / 32768.0f,
                "Planar channels or normalized samples differ");
    raw = nullptr;
    success(swr_alloc_set_opts2(&raw, &mono, AV_SAMPLE_FMT_FLT, 24000,
                              &mono, AV_SAMPLE_FMT_S16, 48000, 0, nullptr), "allocate resampler");
    Resampler rate(raw); success(swr_init(rate.get()), "init resampler");
    std::vector<int16_t> samples(1000, 8192);
    std::vector<float> result(1200, -9.0f);
    const uint8_t *source[]{reinterpret_cast<const uint8_t *>(samples.data())};
    uint8_t *destination[]{reinterpret_cast<uint8_t *>(result.data())};
    int count = swr_convert(rate.get(), destination, 1200, source, 1000);
    success(count, "convert rate");
    for (int attempt = 0; attempt < 10; ++attempt) {
        destination[0] = reinterpret_cast<uint8_t *>(result.data() + count);
        const int got = swr_convert(rate.get(), destination, 1200 - count, nullptr, 0);
        success(got, "drain resampler");
        count += got;
        if (!got) break;
    }
    require(count >= 499 && count <= 501, "Resampled duration differs");
    for (int i = 32; i < count - 32; ++i)
        require(std::isfinite(result[i]) && std::abs(result[i] - 0.25f) < 0.0001f,
                "Resampled DC level differs");
    std::printf("resampled_count=%d\n", count);
}

void errors(const std::filesystem::path &directory)
{
    require(!avcodec_find_encoder_by_name("sh3-invalid-codec"), "Unknown codec accepted");
    auto *badScale = sws_getContext(0, 4, AV_PIX_FMT_RGB24, 4, 4, AV_PIX_FMT_RGB24,
                                   SWS_POINT, nullptr, nullptr, nullptr);
    if (badScale) sws_freeContext(badScale);
    require(!badScale, "Zero-width scaler accepted");
    scale();
    AVChannelLayout mono = AV_CHANNEL_LAYOUT_MONO;
    SwrContext *raw = nullptr;
    success(swr_alloc_set_opts2(&raw, &mono, AV_SAMPLE_FMT_S16, 48000,
                              &mono, AV_SAMPLE_FMT_S16, 0, 0, nullptr), "allocate invalid resampler");
    Resampler rate(raw);
    require(swr_init(rate.get()) < 0, "Zero input rate accepted");
    success(av_opt_set_int(rate.get(), "in_sample_rate", 48000, 0), "correct input rate");
    success(swr_init(rate.get()), "recover resampler");
    require(swr_is_initialized(rate.get()), "Recovered resampler not initialized");
    AVIOContext *io = nullptr;
    const auto missing = directory / "missing-directory" / "out.wav";
    require(!std::filesystem::exists(missing.parent_path()), "Negative path unexpectedly exists");
    require(avio_open(&io, missing.c_str(), AVIO_FLAG_WRITE) < 0, "Missing directory accepted");
    if (io) avio_closep(&io);
    const auto valid = directory / "recovered-io.txt";
    success(avio_open(&io, valid.c_str(), AVIO_FLAG_WRITE), "recover output IO");
    avio_write(io, reinterpret_cast<const uint8_t *>("ok"), 2);
    success(avio_closep(&io), "close recovered IO");
    std::ifstream file(valid);
    std::string text((std::istreambuf_iterator<char>(file)), {});
    require(text == "ok", "Recovered IO contents differ");
}

int main(int argc, char **argv)
{
    try {
        require(argc == 3, "Pass test case and output directory");
        const std::string test = argv[1];
        if (test == "profile") profile();
        else if (test == "pcm") pcm();
        else if (test == "video") video();
        else if (test == "wav") wav(argv[2]);
        else if (test == "scale") scale();
        else if (test == "resample") resample();
        else if (test == "errors") errors(argv[2]);
        else throw std::runtime_error("Unknown case");
        std::printf("PASS %s\n", argv[1]);
    } catch (const std::exception &error) {
        std::fprintf(stderr, "FAIL: %s\n", error.what());
        return 1;
    }
}
