#pragma once

#include <cstdint>

#pragma pack(push, 1)

// Packet Types
enum class PacketType : uint16_t {
    Handshake = 0x00,
    AudioFrame = 0x01,
    ConfigCommand = 0x02,
    StatusMessage = 0x03,
    GracefulShutdown = 0x04,
    // Reserved for future
    Heartbeat = 0x05,
    Debug = 0x06,
    Metrics = 0x07,
    Capabilities = 0x08
};

// Configurable Output Mode
enum class FFTOutputMode : uint8_t {
    BandsOnly = 0,
    Bins64 = 1,
    Bins128 = 2,
    Bins256 = 3,
    BinsFull = 4 // Up to 1024
};

// Standard Packet Header
struct PacketHeader {
    uint32_t magic;           // 'PAND' (0x444E4150)
    uint16_t protocolVersion; // e.g. 1
    PacketType packetType;    
    uint32_t payloadSize;     // Size of the payload following this header
};

// Handshake Payload (Engine -> UI on connect)
struct HandshakePayload {
    uint32_t engineVersion;
    uint32_t supportedCapabilities; // Bitmask of features
    uint32_t enginePID;
};

// AudioFrame Payload (Engine -> UI)
struct AudioFramePayload {
    uint64_t sequenceNumber;
    uint64_t timestampMs; // Milliseconds since epoch at DSP completion

    float peak;
    float rms;
    float pan; // -1.0 (Left) to 1.0 (Right)

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
    FFTOutputMode outputMode;
    uint16_t numBins;
    
    // float rawBins[numBins] follows immediately after this struct in the byte stream
};

// ConfigCommand Payload (UI -> Engine)
struct ConfigCommandPayload {
    // Flags to indicate which settings to update
    bool updateOutputMode;
    bool updateSmoothing;
    bool updateTargetPID;
    
    FFTOutputMode newOutputMode;
    float newSmoothingFactor;
    uint32_t newTargetPID;
};

// StatusMessage Payload (Engine -> UI)
struct StatusPayload {
    uint32_t statusCode; // 0 = OK, 1 = Error, 2 = Target Exited
    // char message[payloadSize - sizeof(uint32_t)] follows
};

#pragma pack(pop)
