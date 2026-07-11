#include <iostream>
#include <string>
#include <chrono>
#include <cmath>
#include <vector>
#include <cstring>
#include <thread>
#include "capture/AudioCapture.h"
#include "dsp/FFTEngine.h"
#include "ipc/IPCServer.h"

// Atomic flag for graceful shutdown
std::atomic<bool> g_running{true};

int main(int argc, char* argv[]) {
    if (argc < 2) {
        std::cerr << "Usage: AudioCaptureService <PID>" << std::endl;
        return 1;
    }
    DWORD pid = std::stoul(argv[1]);

    std::cout << "Starting Audio Capture Service for PID " << pid << "..." << std::endl;

    AudioCapture* capture = new AudioCapture(pid);
    if (!capture->Initialize()) {
        std::cerr << "Failed to initialize AudioCapture." << std::endl;
        delete capture;
        return 1;
    }

    // Configure DSP
    FFTConfig config;
    config.sampleRate = 48000;
    config.channels = 2;
    config.fftSize = 2048;
    config.smoothingFactor = 0.8f;
    
    FFTEngine fftEngine(config);

    std::cout << "Capture & FFT initialized." << std::endl;

    IPCServer ipcServer;
    ipcServer.SetCommandCallback([&](const ConfigCommandPayload& cmd) {
        std::cout << "[IPC] Received ConfigCommand. OutputMode=" << (int)cmd.newOutputMode << std::endl;
        fftEngine.UpdateConfig(cmd);
        if (cmd.updateTargetPID && cmd.newTargetPID != pid) {
            std::cout << "[IPC] Target PID change requested. (Requires process restart in current arch)" << std::endl;
            // In a fully dynamic arch, we'd stop capture, re-initialize AudioCapture with new PID.
        }
    });
    ipcServer.SetShutdownCallback([&]() {
        std::cout << "[IPC] Graceful shutdown requested." << std::endl;
        g_running = false;
    });

    if (!ipcServer.Start()) {
        std::cerr << "Failed to start IPC Server." << std::endl;
    } else {
        std::cout << "IPC Server running. Pipe: \\\\.\\pipe\\PandoraAudioEngine_" << GetCurrentProcessId() << std::endl;
    }

    auto nextUpdate = std::chrono::steady_clock::now();
    const auto updateInterval = std::chrono::microseconds(16666); // ~60fps

    uint64_t sequenceNumber = 0;
    
    while (g_running) {
        auto now = std::chrono::steady_clock::now();
        
        if (now >= nextUpdate) {
            // 1. Drain the lock-free queue into a temporary buffer
            std::vector<float> pcmChunk;
            float sample_l, sample_r;
            
            if (config.channels == 2) {
                while (capture->pcmQueue.try_dequeue(sample_l)) {
                    // We must immediately get the right channel to keep alignment.
                    // If it's not ready yet, we wait a tiny bit or just break.
                    // But CaptureThread always pushes in pairs, so it should be there.
                    while (!capture->pcmQueue.try_dequeue(sample_r)) {
                        // Busy-wait briefly if the producer is between L and R
                        std::this_thread::yield();
                    }
                    pcmChunk.push_back(sample_l);
                    pcmChunk.push_back(sample_r);
                }
            } else {
                float sample;
                while (capture->pcmQueue.try_dequeue(sample)) {
                    pcmChunk.push_back(sample);
                }
            }
            
            // 2. Push to FFT engine
            if (!pcmChunk.empty()) {
                size_t numFrames = pcmChunk.size() / config.channels;
                fftEngine.PushAudio(pcmChunk.data(), numFrames);
            }
            
            // 3. Process DSP
            AudioFramePayload frameData;
            std::vector<float> rawBins;
            
            if (fftEngine.Process(frameData, rawBins)) {
                frameData.sequenceNumber = sequenceNumber++;
                
                // 4. Serialize to IPC
                SerializedPacket packet;
                uint32_t payloadSize = sizeof(AudioFramePayload) + (rawBins.size() * sizeof(float));
                packet.data.resize(sizeof(PacketHeader) + payloadSize);
                
                PacketHeader* header = reinterpret_cast<PacketHeader*>(packet.data.data());
                header->magic = 0x444E4150;
                header->protocolVersion = 1;
                header->packetType = PacketType::AudioFrame;
                header->payloadSize = payloadSize;
                
                // Copy payload struct
                std::memcpy(packet.data.data() + sizeof(PacketHeader), &frameData, sizeof(AudioFramePayload));
                
                // Copy raw bins
                if (!rawBins.empty()) {
                    std::memcpy(packet.data.data() + sizeof(PacketHeader) + sizeof(AudioFramePayload), 
                                rawBins.data(), rawBins.size() * sizeof(float));
                }
                
                ipcServer.SendPacket(packet);
            }
            
            nextUpdate += updateInterval;
        } else {
            // Yield until next frame
            std::this_thread::sleep_for(std::chrono::milliseconds(1));
        }
    }

    std::cout << "Shutting down..." << std::endl;
    ipcServer.Stop();
    delete capture;
    return 0;
}
