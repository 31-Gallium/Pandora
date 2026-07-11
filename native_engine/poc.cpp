#define WIN32_LEAN_AND_MEAN
#include <windows.h>
#include <mmdeviceapi.h>
#include <audioclient.h>
#include <audioclientactivationparams.h>
#include <audiopolicy.h>
#include <ksmedia.h>
#include <iostream>
#include <cmath>
#include <thread>
#include <atomic>
#include <string>

#pragma comment(lib, "ole32.lib")
#pragma comment(lib, "Mmdevapi.lib")

std::atomic<bool> g_running = true;

class AudioLoopbackCapture : public IActivateAudioInterfaceCompletionHandler {
public:
    STDMETHODIMP QueryInterface(REFIID riid, void** ppv) {
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

    STDMETHODIMP_(ULONG) AddRef() { return InterlockedIncrement(&m_ref); }
    STDMETHODIMP_(ULONG) Release() {
        ULONG ref = InterlockedDecrement(&m_ref);
        if (ref == 0) delete this;
        return ref;
    }

    STDMETHODIMP ActivateCompleted(IActivateAudioInterfaceAsyncOperation* operation) {
        HRESULT hr = S_OK;
        HRESULT hrActivateResult = S_OK;
        IUnknown* pAudioInterface = nullptr;

        hr = operation->GetActivateResult(&hrActivateResult, &pAudioInterface);
        if (FAILED(hr) || FAILED(hrActivateResult)) {
            std::cerr << "Failed to activate audio interface. hr=" << std::hex << hr << " result=" << hrActivateResult << std::endl;
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
                m_pAudioClient->Start();
                m_pwfx = (WAVEFORMATEX*)CoTaskMemAlloc(sizeof(WAVEFORMATEX));
                *m_pwfx = wfx;
            } else {
                std::cerr << "Initialize failed: " << std::hex << hr << std::endl;
            }
        }
        
        m_activated = true;
        return S_OK;
    }

    AudioLoopbackCapture() : m_ref(1), m_hEvent(CreateEvent(nullptr, FALSE, FALSE, nullptr)) {}
    ~AudioLoopbackCapture() {
        if (m_pAudioClient) m_pAudioClient->Release();
        if (m_pCaptureClient) m_pCaptureClient->Release();
        if (m_pwfx) CoTaskMemFree(m_pwfx);
        if (m_hEvent) CloseHandle(m_hEvent);
    }

    LONG m_ref;
    IAudioClient* m_pAudioClient = nullptr;
    IAudioCaptureClient* m_pCaptureClient = nullptr;
    WAVEFORMATEX* m_pwfx = nullptr;
    HANDLE m_hEvent;
    bool m_activated = false;
};

int main(int argc, char* argv[]) {
    if (argc < 2) {
        std::cerr << "Usage: poc.exe <PID>" << std::endl;
        return 1;
    }
    DWORD pid = std::stoul(argv[1]);
    
    HRESULT hrCo = CoInitializeEx(nullptr, COINIT_APARTMENTTHREADED);
    if (FAILED(hrCo)) {
        std::cerr << "CoInitializeEx failed: " << std::hex << hrCo << std::endl;
    } else {
        std::cout << "CoInitializeEx succeeded: " << std::hex << hrCo << std::endl;
    }
    
    AUDIOCLIENT_ACTIVATION_PARAMS params = {};
    params.ActivationType = AUDIOCLIENT_ACTIVATION_TYPE_PROCESS_LOOPBACK;
    params.ProcessLoopbackParams.ProcessLoopbackMode = PROCESS_LOOPBACK_MODE_INCLUDE_TARGET_PROCESS_TREE;
    params.ProcessLoopbackParams.TargetProcessId = pid;
    
    PROPVARIANT var;
    PropVariantInit(&var);
    var.vt = VT_BLOB;
    var.blob.cbSize = sizeof(params);
    var.blob.pBlobData = (BYTE*)&params;
    
    IActivateAudioInterfaceAsyncOperation* pAsyncOp = nullptr;
    AudioLoopbackCapture* pHandler = new AudioLoopbackCapture();
    
    HRESULT hr = ActivateAudioInterfaceAsync(L"VAD\\Process_Loopback", __uuidof(IAudioClient), &var, pHandler, &pAsyncOp);
    if (FAILED(hr)) {
        std::cerr << "ActivateAudioInterfaceAsync failed: " << std::hex << hr << std::endl;
        return 1;
    }
    
    while (!pHandler->m_activated) {
        Sleep(10);
    }
    
    if (!pHandler->m_pCaptureClient) {
        std::cerr << "Failed to setup capture client." << std::endl;
        return 1;
    }
    
    std::cout << "Capturing audio for PID " << pid << "..." << std::endl;
    
    int cycles = 0;
    while (g_running && cycles < 100) { // Run for 100 loops of valid audio
        DWORD waitResult = WaitForSingleObject(pHandler->m_hEvent, 100);
        if (waitResult == WAIT_OBJECT_0) {
            BYTE* pData;
            UINT32 numFramesAvailable;
            DWORD flags;
            
            hr = pHandler->m_pCaptureClient->GetBuffer(&pData, &numFramesAvailable, &flags, nullptr, nullptr);
            if (SUCCEEDED(hr)) {
                if (numFramesAvailable > 0) {
                    if (flags & AUDCLNT_BUFFERFLAGS_SILENT) {
                        // Silent
                    } else {
                        if (pHandler->m_pwfx->wFormatTag == WAVE_FORMAT_EXTENSIBLE) {
                            WAVEFORMATEXTENSIBLE* pEx = (WAVEFORMATEXTENSIBLE*)pHandler->m_pwfx;
                            if (pEx->SubFormat == KSDATAFORMAT_SUBTYPE_IEEE_FLOAT) {
                                float* pFloatData = (float*)pData;
                                int channels = pHandler->m_pwfx->nChannels;
                                float peak = 0.0f;
                                float rms = 0.0f;
                                
                                for (UINT32 i = 0; i < numFramesAvailable * channels; ++i) {
                                    float val = pFloatData[i];
                                    if (std::abs(val) > peak) peak = std::abs(val);
                                    rms += val * val;
                                }
                                rms = std::sqrt(rms / (numFramesAvailable * channels));
                                
                                std::cout << "Frames: " << numFramesAvailable << " | Peak: " << peak << " | RMS: " << rms << std::endl;
                                cycles++;
                            }
                        }
                    }
                }
                pHandler->m_pCaptureClient->ReleaseBuffer(numFramesAvailable);
            }
        }
    }
    
    pHandler->Release();
    CoUninitialize();
    return 0;
}
