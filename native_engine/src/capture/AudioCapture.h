#pragma once

#define WIN32_LEAN_AND_MEAN
#include <windows.h>
#include <mmdeviceapi.h>
#include <audioclient.h>
#include <audiopolicy.h>
#include <ksmedia.h>
#include <audioclientactivationparams.h>

#include <atomic>
#include <thread>
#include <functional>
#include <memory>
#include <string>

#include "../../third_party/readerwriterqueue.h"

class AudioCapture : public IActivateAudioInterfaceCompletionHandler {
public:
    AudioCapture(DWORD targetPID);
    ~AudioCapture();

    // COM IUnknown
    STDMETHODIMP QueryInterface(REFIID riid, void** ppv) override;
    STDMETHODIMP_(ULONG) AddRef() override;
    STDMETHODIMP_(ULONG) Release() override;

    // IActivateAudioInterfaceCompletionHandler
    STDMETHODIMP ActivateCompleted(IActivateAudioInterfaceAsyncOperation* operation) override;

    bool Initialize();
    void Stop();

    // The lock-free queue for PCM float data (stereo)
    moodycamel::ReaderWriterQueue<float> pcmQueue;

private:
    void CaptureThread();

    LONG m_ref;
    DWORD m_targetPID;
    std::atomic<bool> m_running;
    std::atomic<bool> m_activated;
    std::atomic<bool> m_hasError;

    HANDLE m_hEvent;
    std::thread m_captureThread;

    IAudioClient* m_pAudioClient;
    IAudioCaptureClient* m_pCaptureClient;
    WAVEFORMATEX* m_pwfx;
};
