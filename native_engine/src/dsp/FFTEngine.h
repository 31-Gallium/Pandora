#pragma once

#include <vector>
#include <cstdint>
#include <complex>
#include <mutex>
#include "../ipc/Protocol.h"

struct FFTConfig {
    uint32_t sampleRate = 48000;
    uint16_t channels = 2;
    uint16_t fftSize = 2048;
    float smoothingFactor = 0.8f;
    FFTOutputMode outputMode = FFTOutputMode::BinsFull;
};

class FFTEngine {
public:
    FFTEngine(const FFTConfig& config);
    ~FFTEngine();

    // Push new PCM samples (assumes interleaved if stereo)
    void PushAudio(const float* pcmData, size_t numSamples);

    // Compute FFT on the sliding window and output a populated payload + downsampled raw bins
    bool Process(AudioFramePayload& outFrame, std::vector<float>& outRawBins);

    // Safely update config from IPC thread
    void UpdateConfig(const ConfigCommandPayload& cmd);

private:
    FFTConfig m_config;
    std::vector<float> m_slidingWindow;
    std::vector<float> m_hannWindow;
    std::vector<float> m_fftInput;
    std::vector<std::complex<float>> m_fftOutput;
    
    // Smoothing buffers
    std::vector<float> m_smoothedBins;
    float m_smoothedBands[8] = {0};
    
    size_t m_writePos = 0;
    size_t m_samplesBuffered = 0;
    
    float m_currentPan = 0.0f;
    float m_lastPeak = 0.0f;
    float m_lastRms = 0.0f;
    
    
    std::mutex m_configMutex;

    void ApplyHannWindow();
    void ComputeBands(const std::vector<float>& magnitudes, AudioFramePayload& frame);
    float CalculateBeatStrength(const std::vector<float>& magnitudes);
    void DownsampleBins(const std::vector<float>& fullBins, std::vector<float>& outBins, FFTOutputMode mode);
};
