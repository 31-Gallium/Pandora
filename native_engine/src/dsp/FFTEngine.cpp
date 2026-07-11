#include "FFTEngine.h"
#include <cmath>
#include <algorithm>
#include <iostream>
#include <chrono>
#include "../../third_party/pocketfft_hdronly.h"

#ifndef M_PI
#define M_PI 3.14159265358979323846
#endif

FFTEngine::FFTEngine(const FFTConfig& config) : m_config(config) {
    m_slidingWindow.resize(config.fftSize, 0.0f);
    m_hannWindow.resize(config.fftSize, 0.0f);
    m_fftInput.resize(config.fftSize, 0.0f);
    
    // For a real-to-complex FFT, output has N/2 + 1 complex values
    // pocketfft stores this as a single vector of floats where real and imag are interleaved,
    // or we can use complex<float> directly.
    m_fftOutput.resize(config.fftSize / 2 + 1);
    
    m_smoothedBins.resize(config.fftSize / 2, 0.0f);

    // Precompute Hann window
    for (size_t i = 0; i < config.fftSize; ++i) {
        m_hannWindow[i] = 0.5f * (1.0f - std::cos(2.0f * M_PI * i / (config.fftSize - 1)));
    }
}

FFTEngine::~FFTEngine() {}

void FFTEngine::PushAudio(const float* pcmData, size_t numSamples) {
    int frames = numSamples / m_config.channels;
    
    double sumSqLeft = 0.0;
    double sumSqRight = 0.0;
    float currentPeak = 0.0f;
    

    for (int i = 0; i < frames; ++i) {
        float mono = 0.0f;
        if (m_config.channels == 2) {
            float l = pcmData[i * 2];
            float r = pcmData[i * 2 + 1];
            sumSqLeft += l * l;
            sumSqRight += r * r;
            mono = (l + r) * 0.5f;
            
            float absL = std::abs(l);
            float absR = std::abs(r);
            if (absL > currentPeak) currentPeak = absL;
            if (absR > currentPeak) currentPeak = absR;
        } else {
            for (int c = 0; c < m_config.channels; ++c) {
                float sample = pcmData[i * m_config.channels + c];
                mono += sample;
                float absVal = std::abs(sample);
                if (absVal > currentPeak) currentPeak = absVal;
            }
            mono /= (float)m_config.channels;
        }

        m_slidingWindow[m_writePos] = mono;
        m_writePos = (m_writePos + 1) % m_config.fftSize;
        if (m_samplesBuffered < m_config.fftSize) {
            m_samplesBuffered++;
        }
    }
    
    m_lastPeak = m_lastPeak * 0.5f + currentPeak * 0.5f;
    
    if (m_config.channels == 2 && frames > 0) {
        float rmsLeft = std::sqrt(sumSqLeft / frames);
        float rmsRight = std::sqrt(sumSqRight / frames);
        float sum = rmsLeft + rmsRight;
        
        m_lastRms = m_lastRms * 0.5f + (sum / 2.0f) * 0.5f;
        
        if (sum > 0.001f) {
            float targetPan = (rmsRight - rmsLeft) / sum;
            m_currentPan = m_currentPan * 0.8f + targetPan * 0.2f;
        } else {
            m_currentPan = m_currentPan * 0.9f;
        }
        
        // Protect against NaN/Inf poisoning
        if (std::isnan(m_currentPan) || std::isinf(m_currentPan)) {
            m_currentPan = 0.0f;
        }
    }
}

void FFTEngine::ApplyHannWindow() {
    for (size_t i = 0; i < m_config.fftSize; ++i) {
        // Read from circular buffer starting at oldest sample
        size_t readPos = (m_writePos + i) % m_config.fftSize;
        m_fftInput[i] = m_slidingWindow[readPos] * m_hannWindow[i];
    }
}

bool FFTEngine::Process(AudioFramePayload& outFrame, std::vector<float>& outRawBins) {
    if (m_samplesBuffered < m_config.fftSize) {
        return false; // Not enough data yet
    }

    // Safely copy config that might have been updated by IPC thread
    FFTConfig currentConfig;
    {
        std::lock_guard<std::mutex> lock(m_configMutex);
        currentConfig = m_config;
    }

    ApplyHannWindow();

    pocketfft::shape_t shape = { m_config.fftSize };
    pocketfft::stride_t stride_in = { sizeof(float) };
    pocketfft::stride_t stride_out = { sizeof(std::complex<float>) };
    size_t axes = 0;

    // pocketfft::r2c signature: shape, stride_in, stride_out, axis, forward, data_in, data_out, fct
    pocketfft::r2c<float>(shape, stride_in, stride_out, axes, true, m_fftInput.data(), m_fftOutput.data(), 1.0f);

    uint16_t numBins = m_config.fftSize / 2;
    outRawBins.resize(numBins);
    
    float peakMagnitude = 0.0f;
    float maxLogMag = 0.0f;
    
    std::vector<float> currentMagnitudes(numBins, 0.0f);

    // Calculate magnitudes and scale logarithmically
    for (size_t i = 0; i < numBins; ++i) {
        float real = m_fftOutput[i].real();
        float imag = m_fftOutput[i].imag();
        
        // Magnitude
        float mag = std::sqrt(real * real + imag * imag);
        
        // Normalize by FFT size
        mag /= m_config.fftSize;
        
        currentMagnitudes[i] = mag;

        // Logarithmic scale (dB) clamped and normalized to 0.0 - 1.0
        // 20 * log10(mag)
        float logMag = 0.0f;
        if (mag > 0.0001f) {
            logMag = 20.0f * std::log10(mag);
            // Example mapping: -80dB to 0dB -> 0.0 to 1.0
            logMag = (logMag + 80.0f) / 80.0f;
            logMag = std::clamp(logMag, 0.0f, 1.0f);
        }

        // Temporal smoothing
        m_smoothedBins[i] = currentConfig.smoothingFactor * m_smoothedBins[i] + (1.0f - currentConfig.smoothingFactor) * logMag;
    }

    // Process Frequency Bands (Uses raw bins, handles its own smoothing internally)
    ComputeBands(currentMagnitudes, outFrame);

    // Downsample the smoothed bins according to requested UI mode
    DownsampleBins(m_smoothedBins, outRawBins, currentConfig.outputMode);

    // Populate remaining metadata
    outFrame.timestampMs = std::chrono::duration_cast<std::chrono::milliseconds>(std::chrono::system_clock::now().time_since_epoch()).count();
    
    outFrame.sampleRate = currentConfig.sampleRate;
    outFrame.channels = currentConfig.channels;
    outFrame.fftSize = currentConfig.fftSize;
    outFrame.outputMode = currentConfig.outputMode;
    outFrame.numBins = (uint16_t)outRawBins.size();
    outFrame.dominantFrequency = 0.0f; 
    outFrame.beatStrength = CalculateBeatStrength(currentMagnitudes);
    outFrame.pan = m_currentPan;
    outFrame.peak = m_lastPeak;
    outFrame.rms = m_lastRms;

    return true;
}

void FFTEngine::ComputeBands(const std::vector<float>& magnitudes, AudioFramePayload& frame) {
    float hzPerBin = (float)m_config.sampleRate / (float)m_config.fftSize;
    
    // Helper lambda to calculate average energy in a frequency range
    auto calcBand = [&](float startHz, float endHz) -> float {
        int startBin = std::max(1, (int)(startHz / hzPerBin));
        int endBin = std::min((int)magnitudes.size() - 1, (int)(endHz / hzPerBin));
        
        if (startBin > endBin) return 0.0f;
        
        float sum = 0.0f;
        for (int i = startBin; i <= endBin; ++i) {
            float logMag = 0.0f;
            if (magnitudes[i] > 0.0001f) {
                logMag = 20.0f * std::log10(magnitudes[i]);
                logMag = (logMag + 80.0f) / 80.0f;
                logMag = std::clamp(logMag, 0.0f, 1.0f);
            }
            sum += logMag;
        }
        return sum / (endBin - startBin + 1);
    };

    // Standard logical bands
    float subBass = calcBand(20.0f, 60.0f);
    float bass = calcBand(60.0f, 250.0f);
    float lowMid = calcBand(250.0f, 500.0f);
    float mid = calcBand(500.0f, 2000.0f);
    float upperMid = calcBand(2000.0f, 4000.0f);
    float presence = calcBand(4000.0f, 6000.0f);
    float treble = calcBand(6000.0f, 10000.0f);
    float air = calcBand(10000.0f, 20000.0f);

    // Apply smoothing
    auto smooth = [&](int index, float newValue) -> float {
        float factor = 0.8f; // Could use currentConfig.smoothingFactor if passed down
        m_smoothedBands[index] = factor * m_smoothedBands[index] + (1.0f - factor) * newValue;
        return m_smoothedBands[index];
    };

    frame.subBass = smooth(0, subBass);
    frame.bass = smooth(1, bass);
    frame.lowMid = smooth(2, lowMid);
    frame.mid = smooth(3, mid);
    frame.upperMid = smooth(4, upperMid);
    frame.presence = smooth(5, presence);
    frame.treble = smooth(6, treble);
    frame.air = smooth(7, air);
}

void FFTEngine::DownsampleBins(const std::vector<float>& fullBins, std::vector<float>& outBins, FFTOutputMode mode) {
    if (mode == FFTOutputMode::BandsOnly) {
        outBins.clear();
        return;
    }
    
    if (mode == FFTOutputMode::BinsFull) {
        outBins = fullBins;
        return;
    }
    
    int targetSize = 0;
    if (mode == FFTOutputMode::Bins64) targetSize = 64;
    else if (mode == FFTOutputMode::Bins128) targetSize = 128;
    else if (mode == FFTOutputMode::Bins256) targetSize = 256;
    else targetSize = fullBins.size();
    
    outBins.resize(targetSize, 0.0f);
    
    if (targetSize >= fullBins.size()) {
        outBins = fullBins;
        return;
    }
    
    float ratio = (float)fullBins.size() / (float)targetSize;
    for (int i = 0; i < targetSize; ++i) {
        int start = (int)(i * ratio);
        int end = (int)((i + 1) * ratio);
        if (end > fullBins.size()) end = fullBins.size();
        
        float maxVal = 0.0f; // Use peak value in the bucket to preserve transient spikes
        for (int j = start; j < end; ++j) {
            if (fullBins[j] > maxVal) {
                maxVal = fullBins[j];
            }
        }
        outBins[i] = maxVal;
    }
}

void FFTEngine::UpdateConfig(const ConfigCommandPayload& cmd) {
    std::lock_guard<std::mutex> lock(m_configMutex);
    if (cmd.updateOutputMode) {
        m_config.outputMode = cmd.newOutputMode;
    }
    if (cmd.updateSmoothing) {
        m_config.smoothingFactor = cmd.newSmoothingFactor;
    }
    // Note: PID change requires restarting the audio capture service, so handled in main.cpp
}

float FFTEngine::CalculateBeatStrength(const std::vector<float>& ) {
    // Simple spectral flux or just bass energy for now
    // A proper beat detector would track energy history and look for spikes
    return m_smoothedBands[0]; // SubBass as rough proxy for beat
}
