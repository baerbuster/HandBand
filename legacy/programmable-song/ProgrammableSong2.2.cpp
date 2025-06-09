#include <iostream>
#include <portaudio.h>
#include <sndfile.h>

#define FRAMES_PER_BUFFER 512

struct AudioData {
    SNDFILE* file;
    SF_INFO info;
};

static int paCallback(const void* inputBuffer, void* outputBuffer,
                      unsigned long framesPerBuffer,
                      const PaStreamCallbackTimeInfo* timeInfo,
                      PaStreamCallbackFlags statusFlags,
                      void* userData) {
    AudioData* data = (AudioData*)userData;
    float* out = (float*)outputBuffer;
    sf_count_t readcount = sf_readf_float(data->file, out, framesPerBuffer);

    if (readcount < framesPerBuffer) {
        // Fill remaining buffer with zeros (silence)
        for (unsigned long i = readcount * data->info.channels; i < framesPerBuffer * data->info.channels; i++) {
            out[i] = 0.0f;
        }
        return paComplete;
    }
    return paContinue;
}

int main(int argc, char* argv[]) {
    if (argc < 2) {
        std::cerr << "Usage: ./playaudio <filename.wav>\n";
        return 1;
    }

    const char* filename = argv[1];
    SF_INFO sfinfo;
    SNDFILE* sndfile = sf_open(filename, SFM_READ, &sfinfo);
    if (!sndfile) {
        std::cerr << "Failed to open file: " << filename << "\n";
        return 1;
    }

    PaError err = Pa_Initialize();
    if (err != paNoError) {
        std::cerr << "PortAudio init error: " << Pa_GetErrorText(err) << "\n";
        sf_close(sndfile);
        return 1;
    }

    AudioData data = { sndfile, sfinfo };

    PaStream* stream;
    err = Pa_OpenDefaultStream(&stream,
                               0, // no input channels
                               sfinfo.channels, // output channels (mono=1, stereo=2)
                               paFloat32,
                               sfinfo.samplerate,
                               FRAMES_PER_BUFFER,
                               paCallback,
                               &data);
    if (err != paNoError) {
        std::cerr << "PortAudio open stream error: " << Pa_GetErrorText(err) << "\n";
        sf_close(sndfile);
        Pa_Terminate();
        return 1;
    }

    err = Pa_StartStream(stream);
    if (err != paNoError) {
        std::cerr << "PortAudio start stream error: " << Pa_GetErrorText(err) << "\n";
        Pa_CloseStream(stream);
        sf_close(sndfile);
        Pa_Terminate();
        return 1;
    }

    std::cout << "Playing " << filename << "...\n";

    while ((err = Pa_IsStreamActive(stream)) == 1) {
        Pa_Sleep(100);
    }

    if (err < 0) {
        std::cerr << "PortAudio stream error: " << Pa_GetErrorText(err) << "\n";
    }

    Pa_StopStream(stream);
    Pa_CloseStream(stream);
    Pa_Terminate();
    sf_close(sndfile);

    std::cout << "Playback finished.\n";
    return 0;
}
