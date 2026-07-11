#pragma once

#include <cstdint>
#include <vector>

#pragma pack(push, 1)
struct AudioFrameHeader {
    uint32_t magic;              // 'PAND'
    uint16_t protocolVersion;    // 1
    uint16_t packetType;         // 1 = AudioFrame
    uint32_t packetSize;         // Total size including this header
};

struct AudioFrameData {
    uint64_t timestamp;

    float peak;
    float rms;

    // Processed frequency bands
    float subBass;
    float bass;
    float lowMid;
    float mid;
    float upperMid;
    float presence;
    float treble;
    float air;

    float dominantFrequency;
    float beatStrength;
    
    // Metadata
    uint32_t sampleRate;
    uint16_t channels;
    uint16_t fftSize;
    uint16_t numBins;
    
    // float rawBins[numBins] follows immediately after in the byte stream
};
#pragma pack(pop)
