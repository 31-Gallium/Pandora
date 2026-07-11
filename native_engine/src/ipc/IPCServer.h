#pragma once

#define WIN32_LEAN_AND_MEAN
#include <windows.h>
#include <string>
#include <thread>
#include <atomic>
#include <vector>
#include <functional>
#include "Protocol.h"
#include "../../third_party/readerwriterqueue.h"

// A structure to hold raw bytes representing a serialized packet
struct SerializedPacket {
    std::vector<uint8_t> data;
};

class IPCServer {
public:
    IPCServer();
    ~IPCServer();

    bool Start();
    void Stop();

    // DSP thread calls this. It's lock-free.
    bool SendPacket(const SerializedPacket& packet);

    // Callbacks for the main loop to process received commands
    using CommandCallback = std::function<void(const ConfigCommandPayload&)>;
    using ShutdownCallback = std::function<void()>;
    
    void SetCommandCallback(CommandCallback cb) { m_commandCallback = cb; }
    void SetShutdownCallback(ShutdownCallback cb) { m_shutdownCallback = cb; }

private:
    void ServerThread();
    void HandleClient(HANDLE hPipe);
    void SendHandshake(HANDLE hPipe);
    bool ReadCommand(HANDLE hPipe);

    std::atomic<bool> m_running;
    std::thread m_serverThread;
    
    CommandCallback m_commandCallback;
    ShutdownCallback m_shutdownCallback;

    // Queue of packets to send to the connected client
    moodycamel::ReaderWriterQueue<SerializedPacket> m_sendQueue;
};
