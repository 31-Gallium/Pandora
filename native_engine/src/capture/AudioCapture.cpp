#include "AudioCapture.h"
#include <iostream>
#include <cmath>

#pragma comment(lib, "ole32.lib")
#pragma comment(lib, "Mmdevapi.lib")

AudioCapture::AudioCapture(DWORD targetPID)
    : m_ref(1), m_targetPID(targetPID), m_running(false), m_activated(false), m_hasError(false),
      m_pAudioClient(nullptr), m_pCaptureClient(nullptr), m_pwfx(nullptr),
      pcmQueue(1000000) // Buffer for up to 1 million floats
{
    m_hEvent = CreateEvent(nullptr, FALSE, FALSE, nullptr);
}

AudioCapture::~AudioCapture() {
    Stop();
    if (m_pAudioClient) m_pAudioClient->Release();
    if (m_pCaptureClient) m_pCaptureClient->Release();
    if (m_pwfx) CoTaskMemFree(m_pwfx);
    if (m_hEvent) CloseHandle(m_hEvent);
}

STDMETHODIMP AudioCapture::QueryInterface(REFIID riid, void** ppv) {
    if (!ppv) return E_POINTER;
    if (riid == IID_IUnknown || 
        riid == __uuidof(IActivateAudioInterfaceCompletionHandler) ||
        riid == __uuidof(IAgileObject)) {
        *ppv = static_cast<IActivateAudioInterfaceCompletionHandler*>(this);
        AddRef();
        return S_OK;
    }
    *ppv = nullptr;
    return E_NOINTERFACE;
}

STDMETHODIMP_(ULONG) AudioCapture::AddRef() {
    return InterlockedIncrement(&m_ref);
}

STDMETHODIMP_(ULONG) AudioCapture::Release() {
    ULONG ref = InterlockedDecrement(&m_ref);
    if (ref == 0) delete this;
    return ref;
}

STDMETHODIMP AudioCapture::ActivateCompleted(IActivateAudioInterfaceAsyncOperation* operation) {
    HRESULT hr = S_OK;
    HRESULT hrActivateResult = S_OK;
    IUnknown* pAudioInterface = nullptr;

    hr = operation->GetActivateResult(&hrActivateResult, &pAudioInterface);
    if (FAILED(hr) || FAILED(hrActivateResult)) {
        m_hasError = true;
        m_activated = true;
        return S_OK;
    }

    pAudioInterface->QueryInterface(__uuidof(IAudioClient), (void**)&m_pAudioClient);
    pAudioInterface->Release();

    if (m_pAudioClient) {
        WAVEFORMATEX wfx = {};
        wfx.wFormatTag = WAVE_FORMAT_IEEE_FLOAT;
        wfx.nChannels = 2;
        wfx.nSamplesPerSec = 48000;
        wfx.wBitsPerSample = 32;
        wfx.nBlockAlign = (wfx.nChannels * wfx.wBitsPerSample) / 8;
        wfx.nAvgBytesPerSec = wfx.nSamplesPerSec * wfx.nBlockAlign;
        wfx.cbSize = 0;

        hr = m_pAudioClient->Initialize(AUDCLNT_SHAREMODE_SHARED,
                                        AUDCLNT_STREAMFLAGS_LOOPBACK | AUDCLNT_STREAMFLAGS_EVENTCALLBACK | AUDCLNT_STREAMFLAGS_AUTOCONVERTPCM | AUDCLNT_STREAMFLAGS_SRC_DEFAULT_QUALITY,
                                        10000000, 0, &wfx, nullptr);
        if (SUCCEEDED(hr)) {
            m_pAudioClient->SetEventHandle(m_hEvent);
            m_pAudioClient->GetService(__uuidof(IAudioCaptureClient), (void**)&m_pCaptureClient);
            m_pwfx = (WAVEFORMATEX*)CoTaskMemAlloc(sizeof(WAVEFORMATEX));
            *m_pwfx = wfx;
        } else {
            m_hasError = true;
        }
    }
    
    m_activated = true;
    return S_OK;
}

bool AudioCapture::Initialize() {
    HRESULT hr = CoInitializeEx(nullptr, COINIT_MULTITHREADED);
    
    AUDIOCLIENT_ACTIVATION_PARAMS params = {};
    params.ActivationType = AUDIOCLIENT_ACTIVATION_TYPE_PROCESS_LOOPBACK;
    params.ProcessLoopbackParams.ProcessLoopbackMode = PROCESS_LOOPBACK_MODE_INCLUDE_TARGET_PROCESS_TREE;
    params.ProcessLoopbackParams.TargetProcessId = m_targetPID;
    
    PROPVARIANT var;
    PropVariantInit(&var);
    var.vt = VT_BLOB;
    var.blob.cbSize = sizeof(params);
    var.blob.pBlobData = (BYTE*)&params;
    
    IActivateAudioInterfaceAsyncOperation* pAsyncOp = nullptr;
    
    hr = ActivateAudioInterfaceAsync(L"VAD\\Process_Loopback", __uuidof(IAudioClient), &var, this, &pAsyncOp);
    if (FAILED(hr)) {
        return false;
    }
    
    // Wait for callback
    while (!m_activated) {
        Sleep(10);
    }
    
    if (m_hasError || !m_pCaptureClient) {
        return false;
    }
    
    // Start capture loop
    m_running = true;
    hr = m_pAudioClient->Start();
    if (FAILED(hr)) return false;

    m_captureThread = std::thread(&AudioCapture::CaptureThread, this);
    return true;
}

void AudioCapture::Stop() {
    m_running = false;
    if (m_hEvent) {
        SetEvent(m_hEvent); // Wake up thread if waiting
    }
    if (m_captureThread.joinable()) {
        m_captureThread.join();
    }
    if (m_pAudioClient) {
        m_pAudioClient->Stop();
    }
}

void AudioCapture::CaptureThread() {
    CoInitializeEx(nullptr, COINIT_MULTITHREADED);

    while (m_running) {
        DWORD waitResult = WaitForSingleObject(m_hEvent, 100);
        if (waitResult == WAIT_OBJECT_0) {
            BYTE* pData;
            UINT32 numFramesAvailable;
            DWORD flags;
            
            HRESULT hr = m_pCaptureClient->GetBuffer(&pData, &numFramesAvailable, &flags, nullptr, nullptr);
            if (SUCCEEDED(hr)) {
                if (numFramesAvailable > 0) {
                    if (flags & AUDCLNT_BUFFERFLAGS_SILENT) {
                        // Push 0s if silent
                        int channels = m_pwfx->nChannels;
                        for (UINT32 i = 0; i < numFramesAvailable * channels; ++i) {
                            pcmQueue.enqueue(0.0f);
                        }
                    } else {
                        float* pFloatData = (float*)pData;
                        int channels = m_pwfx->nChannels;
                        for (UINT32 i = 0; i < numFramesAvailable * channels; ++i) {
                            pcmQueue.enqueue(pFloatData[i]);
                        }
                    }
                }
                m_pCaptureClient->ReleaseBuffer(numFramesAvailable);
            }
        }
    }

    CoUninitialize();
}
