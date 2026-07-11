#include "IPCServer.h"
#include <iostream>

IPCServer::IPCServer() : m_running(false), m_sendQueue(1000) {}

IPCServer::~IPCServer() {
    Stop();
}

bool IPCServer::Start() {
    if (m_running) return false;
    m_running = true;
    m_serverThread = std::thread(&IPCServer::ServerThread, this);
    return true;
}

void IPCServer::Stop() {
    m_running = false;
    // Connect to the pipe ourselves to unblock ConnectNamedPipe if it's waiting
    DWORD pid = GetCurrentProcessId();
    std::string pipeName = "\\\\.\\pipe\\PandoraAudioEngine_" + std::to_string(pid);
    HANDLE hPipe = CreateFileA(pipeName.c_str(), GENERIC_WRITE, 0, nullptr, OPEN_EXISTING, 0, nullptr);
    if (hPipe != INVALID_HANDLE_VALUE) {
        CloseHandle(hPipe);
    }
    
    if (m_serverThread.joinable()) {
        m_serverThread.join();
    }
}

bool IPCServer::SendPacket(const SerializedPacket& packet) {
    if (!m_running) return false;
    return m_sendQueue.try_enqueue(packet);
}

void IPCServer::SendHandshake(HANDLE hPipe) {
    PacketHeader header;
    header.magic = 0x444E4150; // 'PAND'
    header.protocolVersion = 1;
    header.packetType = PacketType::Handshake;
    header.payloadSize = sizeof(HandshakePayload);

    HandshakePayload payload;
    payload.engineVersion = 1;
    payload.supportedCapabilities = 0xFFFFFFFF; // All features supported
    payload.enginePID = GetCurrentProcessId();

    DWORD written = 0;
    WriteFile(hPipe, &header, sizeof(header), &written, nullptr);
    WriteFile(hPipe, &payload, sizeof(payload), &written, nullptr);
}

void IPCServer::ServerThread() {
    DWORD pid = GetCurrentProcessId();
    std::string pipeName = "\\\\.\\pipe\\PandoraAudioEngine_" + std::to_string(pid);

    while (m_running) {
        HANDLE hPipe = CreateNamedPipeA(
            pipeName.c_str(),
            PIPE_ACCESS_DUPLEX,
            PIPE_TYPE_BYTE | PIPE_READMODE_BYTE | PIPE_WAIT,
            1, // Max instances
            65536, // Out buffer
            65536, // In buffer
            0, // Default timeout
            nullptr // Security attributes
        );

        if (hPipe == INVALID_HANDLE_VALUE) {
            std::cerr << "Failed to create named pipe. Error: " << GetLastError() << std::endl;
            std::this_thread::sleep_for(std::chrono::seconds(1));
            continue;
        }

        std::cout << "Waiting for client connection on " << pipeName << std::endl;

        bool connected = ConnectNamedPipe(hPipe, nullptr) ? true : (GetLastError() == ERROR_PIPE_CONNECTED);

        if (connected && m_running) {
            std::cout << "Client connected!" << std::endl;
            HandleClient(hPipe);
        }

        CloseHandle(hPipe);
    }
}

void IPCServer::HandleClient(HANDLE hPipe) {
    // Clear out any stale packets in the queue
    SerializedPacket dump;
    while(m_sendQueue.try_dequeue(dump));

    SendHandshake(hPipe);

    // Make the pipe non-blocking for reads, or just use PeekNamedPipe
    DWORD mode = PIPE_READMODE_BYTE | PIPE_NOWAIT;
    SetNamedPipeHandleState(hPipe, &mode, nullptr, nullptr);

    while (m_running) {
        // 1. Try to read commands from client
        DWORD bytesAvailable = 0;
        if (PeekNamedPipe(hPipe, nullptr, 0, nullptr, &bytesAvailable, nullptr)) {
            if (bytesAvailable >= sizeof(PacketHeader)) {
                PacketHeader header;
                DWORD bytesRead = 0;
                
                // Switch back to blocking mode just for reading the full packet
                mode = PIPE_READMODE_BYTE | PIPE_WAIT;
                SetNamedPipeHandleState(hPipe, &mode, nullptr, nullptr);
                
                if (ReadFile(hPipe, &header, sizeof(header), &bytesRead, nullptr) && bytesRead == sizeof(header)) {
                    if (header.magic == 0x444E4150) { // 'PAND'
                        if (header.packetType == PacketType::GracefulShutdown) {
                            if (m_shutdownCallback) m_shutdownCallback();
                            m_running = false;
                            break;
                        } else if (header.packetType == PacketType::ConfigCommand && header.payloadSize == sizeof(ConfigCommandPayload)) {
                            ConfigCommandPayload cmd;
                            if (ReadFile(hPipe, &cmd, sizeof(cmd), &bytesRead, nullptr) && bytesRead == sizeof(cmd)) {
                                if (m_commandCallback) m_commandCallback(cmd);
                            }
                        } else {
                            // Discard unknown payload
                            std::vector<uint8_t> discard(header.payloadSize);
                            ReadFile(hPipe, discard.data(), header.payloadSize, &bytesRead, nullptr);
                        }
                    }
                }
                
                // Back to non-blocking
                mode = PIPE_READMODE_BYTE | PIPE_NOWAIT;
                SetNamedPipeHandleState(hPipe, &mode, nullptr, nullptr);
            }
        } else {
            if (GetLastError() == ERROR_BROKEN_PIPE) {
                std::cout << "Client disconnected." << std::endl;
                break;
            }
        }

        // 2. Write outgoing packets
        SerializedPacket packet;
        int sent = 0;
        while (m_sendQueue.try_dequeue(packet) && sent < 10) { // Batch up to 10
            DWORD written = 0;
            if (!WriteFile(hPipe, packet.data.data(), (DWORD)packet.data.size(), &written, nullptr)) {
                if (GetLastError() == ERROR_BROKEN_PIPE || GetLastError() == ERROR_NO_DATA) {
                    std::cout << "Client disconnected during write." << std::endl;
                    return; // exit HandleClient
                }
            }
            sent++;
        }

        std::this_thread::sleep_for(std::chrono::milliseconds(2)); // Prevent 100% CPU on loop
    }
}
