//------------------------------------------------------------------------------
// <copyright file="FTHelper.cpp" company="Microsoft">
//     Copyright (c) Microsoft Corporation.  All rights reserved.
// </copyright>
//------------------------------------------------------------------------------

#include "StdAfx.h"
#include "FTHelper.h"
#include "Visualize.h"

#include <fstream>
#include <sstream>

using namespace std;

#ifdef SAMPLE_OPTIONS
#include "Options.h"
#else
PVOID _opt = NULL;
#endif


#include <nuiapi.h>
#include <shlobj.h>
#include <wchar.h>
#include <devicetopology.h>

#include "WASAPICapture.h"

// Number of milliseconds of acceptable lag between live sound being produced and recording operation.
const int TargetLatency = 20;

/// <summary>
/// Get global ID for specified device.
/// </summary>
/// <param name="pDevice">
/// [in] Audio device for which we're getting global ID.
/// </param>
/// <param name="ppszGlobalId">
/// [out] Global ID corresponding to audio device.
/// </param>
/// <returns>
/// S_OK on success, otherwise failure code.
/// </returns>
HRESULT GetGlobalId(IMMDevice *pDevice, wchar_t **ppszGlobalId)
{
    IDeviceTopology *pTopology = NULL;
    HRESULT hr = S_OK;

    hr = pDevice->Activate(__uuidof(IDeviceTopology), CLSCTX_INPROC_SERVER, NULL, reinterpret_cast<void**>(&pTopology));
    if (SUCCEEDED(hr))
    {
        IConnector *pPlug = NULL;

        hr = pTopology->GetConnector(0, &pPlug);
        if (SUCCEEDED(hr))
        {
            IConnector *pJack = NULL;

            hr = pPlug->GetConnectedTo(&pJack);
            if (SUCCEEDED(hr))
            {
                IPart *pJackAsPart = NULL;
                pJack->QueryInterface(IID_PPV_ARGS(&pJackAsPart));

                hr = pJackAsPart->GetGlobalId(ppszGlobalId);
                SafeRelease(pJackAsPart);
            }

            SafeRelease(pPlug);
        }

        SafeRelease(pTopology);
    }

    return hr;
}

/// <summary>
/// Determine if a global audio device ID corresponds to a Kinect sensor.
/// </summary>
/// <param name="pNuiSensor">
/// [in] A Kinect sensor.
/// </param>
/// <param name="pszGlobalId">
/// [in] Global audio device ID to compare to the Kinect sensor's ID.
/// </param>
/// <returns>
/// true if the global device ID corresponds to the sensor specified, false otherwise.
/// </returns>
bool IsMatchingAudioDevice(INuiSensor *pNuiSensor, wchar_t *pszGlobalId)
{
    // Get USB device name from the sensor
    BSTR arrayName = pNuiSensor->NuiAudioArrayId(); // e.g. "USB\\VID_045E&PID_02BB&MI_02\\7&9FF7F87&0&0002"

    wistring strDeviceName(pszGlobalId); // e.g. "{2}.\\\\?\\usb#vid_045e&pid_02bb&mi_02#7&9ff7f87&0&0002#{6994ad04-93ef-11d0-a3cc-00a0c9223196}\\global/00010001"
    wistring strArrayName(arrayName);

    // Make strings have the same internal delimiters
    wistring::size_type findIndex = strArrayName.find(L'\\');
    while (strArrayName.npos != findIndex)
    {
        strArrayName[findIndex] = L'#';
        findIndex = strArrayName.find(L'\\', findIndex + 1);
    }

    // Try to match USB part names for sensor vs audio device global ID
    bool match = strDeviceName.find(strArrayName) != strDeviceName.npos;

    SysFreeString(arrayName);
    return match;
}

/// <summary>
/// Get an audio device that corresponds to the specified Kinect sensor, if such a device exists.
/// </summary>
/// <param name="pNuiSensor">
/// [in] Kinect sensor for which we'll find a corresponding audio device.
/// </param>
/// <param name="ppDevice">
/// [out] Pointer to hold matching audio device found.
/// </param>
/// <returns>
/// S_OK on success, otherwise failure code.
/// </returns>
HRESULT GetMatchingAudioDevice(INuiSensor *pNuiSensor, IMMDevice **ppDevice)
{
    IMMDeviceEnumerator *pDeviceEnumerator = NULL;
    IMMDeviceCollection *pDdeviceCollection = NULL;
    HRESULT hr = S_OK;

    *ppDevice = NULL;

    hr = CoCreateInstance(__uuidof(MMDeviceEnumerator), NULL, CLSCTX_INPROC_SERVER, IID_PPV_ARGS(&pDeviceEnumerator));
    if (SUCCEEDED(hr))
    {
        hr = pDeviceEnumerator->EnumAudioEndpoints(eCapture, DEVICE_STATE_ACTIVE, &pDdeviceCollection);
        if (SUCCEEDED(hr))
        {
            UINT deviceCount;
            hr = pDdeviceCollection->GetCount(&deviceCount);
            if (SUCCEEDED(hr))
            {
                // Iterate through all active audio capture devices looking for one that matches
                // the specified Kinect sensor.
                for (UINT i = 0 ; i < deviceCount; ++i)
                {
                    IMMDevice *pDevice = NULL;

                    hr = pDdeviceCollection->Item(i, &pDevice);
                    if (SUCCEEDED(hr))
                    {
                        wchar_t *pszGlobalId = NULL;
                        hr = GetGlobalId(pDevice, &pszGlobalId);
                        if (SUCCEEDED(hr) && IsMatchingAudioDevice(pNuiSensor, pszGlobalId))
                        {
                            *ppDevice = pDevice;
                            CoTaskMemFree(pszGlobalId);
                            break;
                        }

                        CoTaskMemFree(pszGlobalId);
                    }

                    SafeRelease(pDevice);
                }
            }

            SafeRelease(pDdeviceCollection);
        }

        SafeRelease(pDeviceEnumerator);
    }

    if (SUCCEEDED(hr) && (NULL == *ppDevice))
    {
        // If nothing went wrong but we haven't found a device, return failure
        hr = E_FAIL;
    }

    return hr;
}

//
//  A wave file consists of:
//
//  RIFF header:    8 bytes consisting of the signature "RIFF" followed by a 4 byte file length.
//  WAVE header:    4 bytes consisting of the signature "WAVE".
//  fmt header:     4 bytes consisting of the signature "fmt " followed by a WAVEFORMATEX 
//  WAVEFORMAT:     <n> bytes containing a waveformat structure.
//  DATA header:    8 bytes consisting of the signature "data" followed by a 4 byte file length.
//  wave data:      <m> bytes containing wave data.
//

//  Header for a WAV file - we define a structure describing the first few fields in the header for convenience.
struct WAVEHEADER
{
    DWORD   dwRiff;                     // "RIFF"
    DWORD   dwSize;                     // Size
    DWORD   dwWave;                     // "WAVE"
    DWORD   dwFmt;                      // "fmt "
    DWORD   dwFmtSize;                  // Wave Format Size
};

//  Static RIFF header, we'll append the format to it.
const BYTE WaveHeaderTemplate[] = 
{
    'R',   'I',   'F',   'F',  0x00,  0x00,  0x00,  0x00, 'W',   'A',   'V',   'E',   'f',   'm',   't',   ' ', 0x00, 0x00, 0x00, 0x00
};

//  Static wave DATA tag.
const BYTE WaveData[] = { 'd', 'a', 't', 'a'};

/// <summary>
/// Write the WAV file header contents. 
/// </summary>
/// <param name="waveFile">
/// [in] Handle to file where header will be written.
/// </param>
/// <param name="pWaveFormat">
/// [in] Format of file to write.
/// </param>
/// <param name="dataSize">
/// Number of bytes of data in file's data section.
/// </param>
/// <returns>
/// S_OK on success, otherwise failure code.
/// </returns>
HRESULT WriteWaveHeader(HANDLE waveFile, const WAVEFORMATEX *pWaveFormat, DWORD dataSize)
{
    DWORD waveHeaderSize = sizeof(WAVEHEADER) + sizeof(WAVEFORMATEX) + pWaveFormat->cbSize + sizeof(WaveData) + sizeof(DWORD);
    WAVEHEADER waveHeader;
    DWORD bytesWritten;

    // Update the sizes in the header
    memcpy_s(&waveHeader, sizeof(waveHeader), WaveHeaderTemplate, sizeof(WaveHeaderTemplate));
    waveHeader.dwSize = waveHeaderSize + dataSize - (2 * sizeof(DWORD));
    waveHeader.dwFmtSize = sizeof(WAVEFORMATEX) + pWaveFormat->cbSize;

    // Write the file header
    if (!WriteFile(waveFile, &waveHeader, sizeof(waveHeader), &bytesWritten, NULL))
    {
        return E_FAIL;
    }

    // Write the format
    if (!WriteFile(waveFile, pWaveFormat, sizeof(WAVEFORMATEX) + pWaveFormat->cbSize, &bytesWritten, NULL))
    {
        return E_FAIL;
    }

    // Write the data header
    if (!WriteFile(waveFile, WaveData, sizeof(WaveData), &bytesWritten, NULL))
    {
        return E_FAIL;
    }

    if (!WriteFile(waveFile, &dataSize, sizeof(dataSize), &bytesWritten, NULL))
    {
        return E_FAIL;
    }

    return S_OK;
}

/// <summary>
/// Create the first connected Kinect sensor found.
/// </summary>
/// <param name="ppNuiSensor">
/// [out] Pointer to hold reference to created INuiSensor object.
/// </param>
/// <returns>
/// S_OK on success, otherwise failure code.
/// </returns>
HRESULT CreateFirstConnected(INuiSensor **ppNuiSensor)
{
    INuiSensor *pNuiSensor = NULL;
    int iSensorCount = 0;
    HRESULT hr = S_OK;

    *ppNuiSensor = NULL;

    hr = NuiGetSensorCount(&iSensorCount);
    if (FAILED(hr))
    {
        return hr;
    }

    // Look at each Kinect sensor
    for (int i = 0; i < iSensorCount; ++i)
    {
        // Create the sensor so we can check status, if we can't create it, move on to the next
        hr = NuiCreateSensorByIndex(i, &pNuiSensor);
        if (FAILED(hr))
        {
            continue;
        }

        // Get the status of the sensor, and if connected, then we can initialize it
        hr = pNuiSensor->NuiStatus();
        if (S_OK == hr)
        {
            *ppNuiSensor = pNuiSensor;
            pNuiSensor = NULL;
            break;
        }

        // This sensor wasn't OK, so release it since we're not using it
        SafeRelease(pNuiSensor);
    }

    if (SUCCEEDED(hr) && (NULL == *ppNuiSensor))
    {
        // If nothing went wrong but we haven't found a sensor, return failure
        hr = E_FAIL;
    }

    SafeRelease(pNuiSensor);
    return hr;
}


FTHelper::FTHelper()
{
    m_pFaceTracker = 0;
    m_hWnd = NULL;
    m_pFTResult = NULL;
    m_colorImage = NULL;
    m_depthImage = NULL;
    m_ApplicationIsRunning = false;
    m_LastTrackSucceeded = false;
    m_CallBack = NULL;
    m_XCenterFace = 0;
    m_YCenterFace = 0;
    m_hFaceTrackingThread = NULL;
    m_DrawMask = TRUE;
    m_depthType = NUI_IMAGE_TYPE_DEPTH;
    m_depthRes = NUI_IMAGE_RESOLUTION_INVALID;
    m_bNearMode = FALSE;
    m_bFallbackToDefault = FALSE;
    m_colorType = NUI_IMAGE_TYPE_COLOR;
    m_colorRes = NUI_IMAGE_RESOLUTION_INVALID;
}

FTHelper::~FTHelper()
{
    Stop();
}

HRESULT FTHelper::Init(HWND hWnd, FTHelperCallBack callBack, PVOID callBackParam, 
                       NUI_IMAGE_TYPE depthType, NUI_IMAGE_RESOLUTION depthRes, BOOL bNearMode, BOOL bFallbackToDefault, NUI_IMAGE_TYPE colorType, NUI_IMAGE_RESOLUTION colorRes, BOOL bSeatedSkeletonMode)
{
    if (!hWnd || !callBack)
    {
        return E_INVALIDARG;
    }
    m_hWnd = hWnd;
    m_CallBack = callBack;
    m_CallBackParam = callBackParam;
    m_ApplicationIsRunning = true;
    m_depthType = depthType;
    m_depthRes = depthRes;
    m_bNearMode = bNearMode;
    m_bFallbackToDefault = bFallbackToDefault;
    m_bSeatedSkeletonMode = bSeatedSkeletonMode;
    m_colorType = colorType;
    m_colorRes = colorRes;
    m_hFaceTrackingThread = CreateThread(NULL, 0, FaceTrackingStaticThread, (PVOID)this, 0, 0);
	frameNum = 0;


	//Step 1: Initialize audio stuff
    pNuiSensor = NULL;
    device = NULL;
    waveFile = INVALID_HANDLE_VALUE;
    capturer = NULL;
	string s = "out.wav";
	wstring sw = std::wstring(s.begin(), s.end());
	LPCWSTR waveFilename = sw.c_str();
	
	CoInitializeEx(NULL, COINIT_APARTMENTTHREADED);
	CreateFirstConnected(&pNuiSensor);
	GetMatchingAudioDevice(pNuiSensor, &device);
	waveFile = CreateFile(waveFilename, GENERIC_WRITE, FILE_SHARE_READ, NULL, CREATE_ALWAYS, 
							FILE_ATTRIBUTE_NORMAL | FILE_FLAG_SEQUENTIAL_SCAN, 
							NULL);
	capturer = new (std::nothrow) CWASAPICapture(device);
	capturer->Initialize(TargetLatency);

	// Write a placeholder wave file header. Actual size of data section will be fixed up later.
    WriteWaveHeader(waveFile, capturer->GetOutputFormat(), 0);
	capturer->Start(waveFile);
	while(capturer->BytesCaptured() == 0) {}
	
	startTime = clock();

    return S_OK;
}

HRESULT FTHelper::Stop()
{
    m_ApplicationIsRunning = false;
    if (m_hFaceTrackingThread)
    {
        WaitForSingleObject(m_hFaceTrackingThread, 1000);
    }
    m_hFaceTrackingThread = 0;

	//Now shut down audio stuff
	capturer->Stop();
	// Fix up the wave file header to reflect the right amount of captured data.
	SetFilePointer(waveFile, 0, NULL, FILE_BEGIN);
	WriteWaveHeader(waveFile, capturer->GetOutputFormat(), capturer->BytesCaptured());
	CloseHandle(waveFile);
    delete capturer;
    SafeRelease(pNuiSensor);
    SafeRelease(device);
    CoUninitialize();

    return S_OK;
}

BOOL FTHelper::SubmitFraceTrackingResult(IFTResult* pResult)
{
    if (pResult != NULL && SUCCEEDED(pResult->GetStatus()))
    {
        if (m_CallBack)
        {
            (*m_CallBack)(m_CallBackParam);
        }

        if (m_DrawMask)
        {
            FLOAT* pSU = NULL;
            UINT numSU;
            BOOL suConverged;
            m_pFaceTracker->GetShapeUnits(NULL, &pSU, &numSU, &suConverged);
            POINT viewOffset = {0, 0};
            FT_CAMERA_CONFIG cameraConfig;
            if (m_KinectSensorPresent)
            {
                m_KinectSensor.GetVideoConfiguration(&cameraConfig);
            }
            else
            {
                cameraConfig.Width = 640;
                cameraConfig.Height = 480;
                cameraConfig.FocalLength = 500.0f;
            }
            IFTModel* ftModel;
            HRESULT hr = m_pFaceTracker->GetFaceModel(&ftModel);
            if (SUCCEEDED(hr))
            {
				//Get time of occurrence of this frame
				double timestamp = (clock() - startTime) / (double) CLOCKS_PER_SEC;

                hr = VisualizeFaceModel(m_colorImage, ftModel, &cameraConfig, pSU, 1.0, viewOffset, pResult, 0x00FFFF00);
				//ADDED BY CHRIS TRALIE
				//Get 3D shape points
				UINT vertexCount = ftModel->GetVertexCount();
				FT_VECTOR3D* pPts3D = reinterpret_cast<FT_VECTOR3D*>(_malloca(sizeof(FT_VECTOR3D) * vertexCount));

				FLOAT *pAUs;
				UINT auCount;
				DWORD bytesCaptured = capturer->BytesCaptured();

				m_pFTResult->GetAUCoefficients(&pAUs, &auCount);
				FLOAT scale, rotationXYZ[3], translationXYZ[3];
				m_pFTResult->Get3DPose(&scale, rotationXYZ, translationXYZ);
				ftModel->Get3DShape(pSU, ftModel->GetSUCount(), pAUs, auCount, scale, rotationXYZ, translationXYZ, pPts3D, vertexCount);
				
				stringstream ss;
				ss << frameNum << ".txt";
				ofstream frameFile;
				frameFile.open(ss.str());
				frameFile << timestamp << " " << bytesCaptured << " 0\n"; 
				for (UINT i = 0; i < vertexCount; i++) {
					frameFile << pPts3D[i].x << " " << pPts3D[i].y << " " << pPts3D[i].z << endl;
				}
				frameFile.close();

				_freea(pPts3D);
				frameNum++;
				//END ADDED CODE
				ftModel->Release();
            }
        }
    }
    return TRUE;
}

// We compute here the nominal "center of attention" that is used when zooming the presented image.
void FTHelper::SetCenterOfImage(IFTResult* pResult)
{
    float centerX = ((float)m_colorImage->GetWidth())/2.0f;
    float centerY = ((float)m_colorImage->GetHeight())/2.0f;
    if (pResult)
    {
        if (SUCCEEDED(pResult->GetStatus()))
        {
            RECT faceRect;
            pResult->GetFaceRect(&faceRect);
            centerX = (faceRect.left+faceRect.right)/2.0f;
            centerY = (faceRect.top+faceRect.bottom)/2.0f;
        }
        m_XCenterFace += 0.02f*(centerX-m_XCenterFace);
        m_YCenterFace += 0.02f*(centerY-m_YCenterFace);
    }
    else
    {
        m_XCenterFace = centerX;
        m_YCenterFace = centerY;
    }
}

// Get a video image and process it.
void FTHelper::CheckCameraInput()
{
    HRESULT hrFT = E_FAIL;

    if (m_KinectSensorPresent && m_KinectSensor.GetVideoBuffer())
    {
        HRESULT hrCopy = m_KinectSensor.GetVideoBuffer()->CopyTo(m_colorImage, NULL, 0, 0);
        if (SUCCEEDED(hrCopy) && m_KinectSensor.GetDepthBuffer())
        {
            hrCopy = m_KinectSensor.GetDepthBuffer()->CopyTo(m_depthImage, NULL, 0, 0);
        }
        // Do face tracking
        if (SUCCEEDED(hrCopy))
        {
            FT_SENSOR_DATA sensorData(m_colorImage, m_depthImage, m_KinectSensor.GetZoomFactor(), m_KinectSensor.GetViewOffSet());

            FT_VECTOR3D* hint = NULL;
            if (SUCCEEDED(m_KinectSensor.GetClosestHint(m_hint3D)))
            {
                hint = m_hint3D;
            }
            if (m_LastTrackSucceeded)
            {
                hrFT = m_pFaceTracker->ContinueTracking(&sensorData, hint, m_pFTResult);
            }
            else
            {
                hrFT = m_pFaceTracker->StartTracking(&sensorData, NULL, hint, m_pFTResult);
            }
        }
    }

    m_LastTrackSucceeded = SUCCEEDED(hrFT) && SUCCEEDED(m_pFTResult->GetStatus());
    if (m_LastTrackSucceeded)
    {
        SubmitFraceTrackingResult(m_pFTResult);
    }
    else
    {
        m_pFTResult->Reset();
    }
    SetCenterOfImage(m_pFTResult);
}

DWORD WINAPI FTHelper::FaceTrackingStaticThread(PVOID lpParam)
{
    FTHelper* context = static_cast<FTHelper*>(lpParam);
    if (context)
    {
        return context->FaceTrackingThread();
    }
    return 0;
}

DWORD WINAPI FTHelper::FaceTrackingThread()
{
    FT_CAMERA_CONFIG videoConfig;
    FT_CAMERA_CONFIG depthConfig;
    FT_CAMERA_CONFIG* pDepthConfig = NULL;

    // Try to get the Kinect camera to work
    HRESULT hr = m_KinectSensor.Init(m_depthType, m_depthRes, m_bNearMode, m_bFallbackToDefault, m_colorType, m_colorRes, m_bSeatedSkeletonMode);
    if (SUCCEEDED(hr))
    {
        m_KinectSensorPresent = TRUE;
        m_KinectSensor.GetVideoConfiguration(&videoConfig);
        m_KinectSensor.GetDepthConfiguration(&depthConfig);
        pDepthConfig = &depthConfig;
        m_hint3D[0] = m_hint3D[1] = FT_VECTOR3D(0, 0, 0);
    }
    else
    {
        m_KinectSensorPresent = FALSE;
        WCHAR errorText[MAX_PATH];
        ZeroMemory(errorText, sizeof(WCHAR) * MAX_PATH);
        wsprintf(errorText, L"Could not initialize the Kinect sensor. hr=0x%x\n", hr);
        MessageBoxW(m_hWnd, errorText, L"Face Tracker Initialization Error\n", MB_OK);
        return 1;
    }

    // Try to start the face tracker.
    m_pFaceTracker = FTCreateFaceTracker(_opt);
    if (!m_pFaceTracker)
    {
        MessageBoxW(m_hWnd, L"Could not create the face tracker.\n", L"Face Tracker Initialization Error\n", MB_OK);
        return 2;
    }

    hr = m_pFaceTracker->Initialize(&videoConfig, pDepthConfig, NULL, NULL); 
    if (FAILED(hr))
    {
        WCHAR path[512], buffer[1024];
        GetCurrentDirectoryW(ARRAYSIZE(path), path);
        wsprintf(buffer, L"Could not initialize face tracker (%s). hr=0x%x", path, hr);

        MessageBoxW(m_hWnd, /*L"Could not initialize the face tracker.\n"*/ buffer, L"Face Tracker Initialization Error\n", MB_OK);

        return 3;
    }

    hr = m_pFaceTracker->CreateFTResult(&m_pFTResult);
    if (FAILED(hr) || !m_pFTResult)
    {
        MessageBoxW(m_hWnd, L"Could not initialize the face tracker result.\n", L"Face Tracker Initialization Error\n", MB_OK);
        return 4;
    }

    // Initialize the RGB image.
    m_colorImage = FTCreateImage();
    if (!m_colorImage || FAILED(hr = m_colorImage->Allocate(videoConfig.Width, videoConfig.Height, FTIMAGEFORMAT_UINT8_B8G8R8X8)))
    {
        return 5;
    }

    if (pDepthConfig)
    {
        m_depthImage = FTCreateImage();
        if (!m_depthImage || FAILED(hr = m_depthImage->Allocate(depthConfig.Width, depthConfig.Height, FTIMAGEFORMAT_UINT16_D13P3)))
        {
            return 6;
        }
    }

    SetCenterOfImage(NULL);
    m_LastTrackSucceeded = false;

    while (m_ApplicationIsRunning)
    {
        CheckCameraInput();
        InvalidateRect(m_hWnd, NULL, FALSE);
        UpdateWindow(m_hWnd);
        Sleep(16);
    }

    m_pFaceTracker->Release();
    m_pFaceTracker = NULL;

    if(m_colorImage)
    {
        m_colorImage->Release();
        m_colorImage = NULL;
    }

    if(m_depthImage) 
    {
        m_depthImage->Release();
        m_depthImage = NULL;
    }

    if(m_pFTResult)
    {
        m_pFTResult->Release();
        m_pFTResult = NULL;
    }
    m_KinectSensor.Release();
    return 0;
}

HRESULT FTHelper::GetCameraConfig(FT_CAMERA_CONFIG* cameraConfig)
{
    return m_KinectSensorPresent ? m_KinectSensor.GetVideoConfiguration(cameraConfig) : E_FAIL;
}
