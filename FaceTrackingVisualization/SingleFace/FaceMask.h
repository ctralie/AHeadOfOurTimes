#pragma once

HRESULT getFaceMask(BOOL* mask, IFTModel* pModel, FT_CAMERA_CONFIG const* pCameraConfig, FLOAT const* pSUCoef,
	FLOAT zoomFactor, POINT viewOffset, IFTResult* pAAMRlt);