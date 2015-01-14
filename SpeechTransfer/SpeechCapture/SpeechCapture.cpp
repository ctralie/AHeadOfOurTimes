//------------------------------------------------------------------------------
// <copyright file="ColorBasics.cpp" company="Microsoft">
//     Copyright (c) Microsoft Corporation.  All rights reserved.
// </copyright>
//------------------------------------------------------------------------------

#include "stdafx.h"
#include <strsafe.h>
#include "SpeechCapture.h"
#include "resource.h"

/// <summary>
/// Entry point for the application
/// </summary>
/// <param name="hInstance">handle to the application instance</param>
/// <param name="hPrevInstance">always 0</param>
/// <param name="lpCmdLine">command line arguments</param>
/// <param name="nCmdShow">whether to display minimized, maximized, or normally</param>
/// <returns>status</returns>
int APIENTRY wWinMain(HINSTANCE hInstance, HINSTANCE hPrevInstance, LPWSTR lpCmdLine, int nCmdShow)
{
    CSpeechCapture application;
    application.Run(hInstance, nCmdShow);
}

/// <summary>
/// Constructor
/// </summary>
CSpeechCapture::CSpeechCapture() :
    m_pD2DFactory(NULL),
    m_pDrawColor(NULL),
    m_hNextColorFrameEvent(INVALID_HANDLE_VALUE),
    m_pColorStreamHandle(INVALID_HANDLE_VALUE),
    m_bSaveScreenshot(false),
    m_pNuiSensor(NULL)
{
}

/// <summary>
/// Destructor
/// </summary>
CSpeechCapture::~CSpeechCapture()
{
    if (m_pNuiSensor)
    {
        m_pNuiSensor->NuiShutdown();
    }

    if (m_hNextColorFrameEvent != INVALID_HANDLE_VALUE)
    {
        CloseHandle(m_hNextColorFrameEvent);
    }

    // clean up Direct2D renderer
    delete m_pDrawColor;
    m_pDrawColor = NULL;

    // clean up Direct2D
    SafeRelease(m_pD2DFactory);

    SafeRelease(m_pNuiSensor);

	//Clean up image buffers
	for (size_t i = 0; i < depthImages.size(); i++) {
		delete[] depthImages[i];
	}
	for (size_t i = 0; i < RGBXImages.size(); i++) {
		delete[] RGBXImages[i];
	}
	for (size_t i = 0; i < colorCoords.size(); i++) {
		delete[] colorCoords[i];
	}
}

/// <summary>
/// Creates the main window and begins processing
/// </summary>
/// <param name="hInstance">handle to the application instance</param>
/// <param name="nCmdShow">whether to display minimized, maximized, or normally</param>
int CSpeechCapture::Run(HINSTANCE hInstance, int nCmdShow)
{
    MSG       msg = {0};
    WNDCLASS  wc;

	counter = 0;

    // Dialog custom window class
    ZeroMemory(&wc, sizeof(wc));
    wc.style         = CS_HREDRAW | CS_VREDRAW;
    wc.cbWndExtra    = DLGWINDOWEXTRA;
    wc.hInstance     = hInstance;
    wc.hCursor       = LoadCursorW(NULL, IDC_ARROW);
    wc.hIcon         = LoadIconW(hInstance, MAKEINTRESOURCE(IDI_APP));
    wc.lpfnWndProc   = DefDlgProcW;
    wc.lpszClassName = L"ColorBasicsAppDlgWndClass";

    if (!RegisterClassW(&wc))
    {
        return 0;
    }

    // Create main application window
    HWND hWndApp = CreateDialogParamW(
        hInstance,
        MAKEINTRESOURCE(IDD_APP),
        NULL,
        (DLGPROC)CSpeechCapture::MessageRouter, 
        reinterpret_cast<LPARAM>(this));

    // Show window
    ShowWindow(hWndApp, nCmdShow);

    const int eventCount = 1;
    HANDLE hEvents[eventCount];

    // Main message loop
    while (WM_QUIT != msg.message)
    {
        hEvents[0] = m_hNextColorFrameEvent;

        // Check to see if we have either a message (by passing in QS_ALLINPUT)
        // Or a Kinect event (hEvents)
        // Update() will check for Kinect events individually, in case more than one are signalled
        DWORD dwEvent = MsgWaitForMultipleObjects(eventCount, hEvents, FALSE, INFINITE, QS_ALLINPUT);

        // Check if this is an event we're waiting on and not a timeout or message
        if (WAIT_OBJECT_0 == dwEvent)
        {
            Update();
        }

        if (PeekMessageW(&msg, NULL, 0, 0, PM_REMOVE))
        {
            // If a dialog message will be taken care of by the dialog proc
            if ((hWndApp != NULL) && IsDialogMessageW(hWndApp, &msg))
            {
                continue;
            }

            TranslateMessage(&msg);
            DispatchMessageW(&msg);
        }
    }

    return static_cast<int>(msg.wParam);
}

/// <summary>
/// Handles window messages, passes most to the class instance to handle
/// </summary>
/// <param name="hWnd">window message is for</param>
/// <param name="uMsg">message</param>
/// <param name="wParam">message data</param>
/// <param name="lParam">additional message data</param>
/// <returns>result of message processing</returns>
LRESULT CALLBACK CSpeechCapture::MessageRouter(HWND hWnd, UINT uMsg, WPARAM wParam, LPARAM lParam)
{
    CSpeechCapture* pThis = NULL;
    
    if (WM_INITDIALOG == uMsg)
    {
        pThis = reinterpret_cast<CSpeechCapture*>(lParam);
        SetWindowLongPtr(hWnd, GWLP_USERDATA, reinterpret_cast<LONG_PTR>(pThis));
    }
    else
    {
        pThis = reinterpret_cast<CSpeechCapture*>(::GetWindowLongPtr(hWnd, GWLP_USERDATA));
    }

    if (pThis)
    {
        return pThis->DlgProc(hWnd, uMsg, wParam, lParam);
    }

    return 0;
}

/// <summary>
/// Handle windows messages for the class instance
/// </summary>
/// <param name="hWnd">window message is for</param>
/// <param name="uMsg">message</param>
/// <param name="wParam">message data</param>
/// <param name="lParam">additional message data</param>
/// <returns>result of message processing</returns>
LRESULT CALLBACK CSpeechCapture::DlgProc(HWND hWnd, UINT message, WPARAM wParam, LPARAM lParam)
{
    switch (message)
    {
        case WM_INITDIALOG:
        {
            // Bind application window handle
            m_hWnd = hWnd;

            // Init Direct2D
            D2D1CreateFactory(D2D1_FACTORY_TYPE_SINGLE_THREADED, &m_pD2DFactory);

            // Create and initialize a new Direct2D image renderer (take a look at ImageRenderer.h)
            // We'll use this to draw the data we receive from the Kinect to the screen
            m_pDrawColor = new ImageRenderer();
            HRESULT hr = m_pDrawColor->Initialize(GetDlgItem(m_hWnd, IDC_VIDEOVIEW), m_pD2DFactory, cColorWidth, cColorHeight, cColorWidth * sizeof(long));
            if (FAILED(hr))
            {
                SetStatusMessage(L"Failed to initialize the Direct2D draw device.");
            }

            // Look for a connected Kinect, and create it if found
            CreateFirstConnected();
        }
        break;

        // If the titlebar X is clicked, destroy app
        case WM_CLOSE:
            DestroyWindow(hWnd);
            break;

        case WM_DESTROY:
            // Quit the main message pump
            PostQuitMessage(0);
            break;

        // Handle button press
        case WM_COMMAND:
            // If it was for the screenshot control and a button clicked event, save a screenshot next frame 
            if (IDC_BUTTON_SCREENSHOT == LOWORD(wParam) && BN_CLICKED == HIWORD(wParam))
            {
                m_bSaveScreenshot = true;
            }
            break;
    }

    return FALSE;
}

/// <summary>
/// Create the first connected Kinect found 
/// </summary>
/// <returns>indicates success or failure</returns>
HRESULT CSpeechCapture::CreateFirstConnected()
{
    INuiSensor * pNuiSensor;
    HRESULT hr;

    int iSensorCount = 0;
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
            m_pNuiSensor = pNuiSensor;
            break;
        }

        // This sensor wasn't OK, so release it since we're not using it
        pNuiSensor->Release();
    }

    if (NULL != m_pNuiSensor)
    {
		// Initialize the Kinect and specify that we'll be using depth
		hr = m_pNuiSensor->NuiInitialize(NUI_INITIALIZE_FLAG_USES_COLOR | NUI_INITIALIZE_FLAG_USES_DEPTH_AND_PLAYER_INDEX);
		if (FAILED(hr)) { return hr; }

		// Create an event that will be signaled when depth data is available
		m_hNextDepthFrameEvent = CreateEvent(NULL, TRUE, FALSE, NULL);

		// Open a depth image stream to receive depth frames
		hr = m_pNuiSensor->NuiImageStreamOpen(
			NUI_IMAGE_TYPE_DEPTH_AND_PLAYER_INDEX,
			NUI_IMAGE_RESOLUTION_640x480,
			0,
			2,
			m_hNextDepthFrameEvent,
			&m_pDepthStreamHandle);
		if (FAILED(hr)) { return hr; }

		// Create an event that will be signaled when color data is available
		m_hNextColorFrameEvent = CreateEvent(NULL, TRUE, FALSE, NULL);

		// Open a color image stream to receive color frames
		hr = m_pNuiSensor->NuiImageStreamOpen(
			NUI_IMAGE_TYPE_COLOR,
			NUI_IMAGE_RESOLUTION_640x480,
			0,
			2,
			m_hNextColorFrameEvent,
			&m_pColorStreamHandle);
		if (FAILED(hr)) { return hr; }
    }

    if (NULL == m_pNuiSensor || FAILED(hr))
    {
        SetStatusMessage(L"No ready Kinect found!");
        return E_FAIL;
    }

    return hr;
}

/// <summary>
/// Main processing function
/// </summary>
void CSpeechCapture::Update()
{
	if (NULL == m_pNuiSensor)
	{
		return;
	}

	if (WAIT_OBJECT_0 == WaitForSingleObject(m_hNextDepthFrameEvent, 0))
	{
		ProcessDepth();
	}

	if (WAIT_OBJECT_0 == WaitForSingleObject(m_hNextColorFrameEvent, 0))
	{
		ProcessColor();
	}

	MapColorToDepth();
	//TODO: Save info along with audio timestamp

	counter++;
}

/// <summary>
/// Handle new color data
/// </summary>
/// <returns>indicates success or failure</returns>
void CSpeechCapture::ProcessColor()
{
    HRESULT hr;
    NUI_IMAGE_FRAME imageFrame;

    // Attempt to get the color frame
    hr = m_pNuiSensor->NuiImageStreamGetNextFrame(m_pColorStreamHandle, 0, &imageFrame);
    if (FAILED(hr))
    {
        return;
    }

    INuiFrameTexture * pTexture = imageFrame.pFrameTexture;
    NUI_LOCKED_RECT LockedRect;

    // Lock the frame data so the Kinect knows not to modify it while we're reading it
    pTexture->LockRect(0, &LockedRect, NULL, 0);

    // Make sure we've received valid data
    if (LockedRect.Pitch != 0)
    {
        // Draw the data with Direct2D
        m_pDrawColor->Draw(static_cast<BYTE *>(LockedRect.pBits), LockedRect.size);
		//Copy the data to the buffer array
		BYTE* m_colorRGBX = new BYTE[640 * 480 * cBytesPerPixel];
		memcpy(m_colorRGBX, LockedRect.pBits, LockedRect.size);
		RGBXImages.push_back(m_colorRGBX);
    }

    // We're done with the texture so unlock it
    pTexture->UnlockRect(0);

    // Release the frame
    m_pNuiSensor->NuiImageStreamReleaseFrame(m_pColorStreamHandle, &imageFrame);
}

void CSpeechCapture::ProcessDepth()
{
	NUI_IMAGE_FRAME imageFrame;

	HRESULT hr = m_pNuiSensor->NuiImageStreamGetNextFrame(m_pDepthStreamHandle, 0, &imageFrame);
	if (FAILED(hr)) { return ; }

	NUI_LOCKED_RECT LockedRect;
	hr = imageFrame.pFrameTexture->LockRect(0, &LockedRect, NULL, 0);
	if (FAILED(hr)) { return ; }

	USHORT* m_depthD16 = new USHORT[640 * 480];
	memcpy(m_depthD16, LockedRect.pBits, LockedRect.size);
	depthImages.push_back(m_depthD16);

	hr = imageFrame.pFrameTexture->UnlockRect(0);
	if (FAILED(hr)) { return ; };

	hr = m_pNuiSensor->NuiImageStreamReleaseFrame(m_pDepthStreamHandle, &imageFrame);
}

/// <summary>
/// Process color data received from Kinect
/// </summary>
/// <returns>S_OK for success, or failure code</returns>
void CSpeechCapture::MapColorToDepth()
{
	HRESULT hr;

	if (depthImages.size() == 0 || RGBXImages.size() == 0 || depthImages.size() != RGBXImages.size()) {
		//Still waiting on depth/rgb images
		return;
	}

	// Get of x, y coordinates for color in depth space
	// This will allow us to later compensate for the differences in location, angle, etc between the depth and color cameras
	LONG* m_colorCoordinates = new LONG[640 * 480 * 2];
	m_pNuiSensor->NuiImageGetColorPixelCoordinateFrameFromDepthPixelFrameAtResolution(
		NUI_IMAGE_RESOLUTION_640x480,
		NUI_IMAGE_RESOLUTION_640x480,
		640*480,
		depthImages[ ((int)depthImages.size()) - 1 ],
		640* 480 * 2,
		m_colorCoordinates
		);

	colorCoords.push_back(m_colorCoordinates);
}

/// <summary>
/// Set the status bar message
/// </summary>
/// <param name="szMessage">message to display</param>
void CSpeechCapture::SetStatusMessage(WCHAR * szMessage)
{
    SendDlgItemMessageW(m_hWnd, IDC_STATUS, WM_SETTEXT, 0, (LPARAM)szMessage);
}