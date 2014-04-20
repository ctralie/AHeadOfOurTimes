//------------------------------------------------------------------------------
// <copyright file="Visualize.cpp" company="Microsoft">
//     Copyright (c) Microsoft Corporation.  All rights reserved.
// </copyright>
//------------------------------------------------------------------------------

#include <stdafx.h>
#include <FaceTrackLib.h>
#include <math.h>

//Go to http://devmaster.net/posts/6145/advanced-rasterization for a faster implementation
//Vertices are specified in clockwise order
void fillTriangle(BOOL* mask, int W, int H, POINT* P1, POINT* P2, POINT* P3) {
	double x1 = (double)P1->x, y1 = (double)P1->y;
	double x2 = (double)P2->x, y2 = (double)P2->y;
	double x3 = (double)P3->x, y3 = (double)P3->y;

	//Line normals
	double N1x = y2 - y1;
	double N1y = x1 - x2;
	double N2x = y3 - y2;
	double N2y = x2 - x3;
	double N3x = y1 - y3;
	double N3y = x3 - x1;

	//Line origin offsets
	double D1 = x1*N1x + y1*N1y;
	double D2 = x2*N2x + y2*N2y;
	double D3 = x3*N3x + y3*N3y;

	//Bounding rectangle
	double xmin = min(x1, min(x2, x3));
	double ymin = min(y1, min(y2, y3));
	double xmax = max(x1, max(x2, x3));
	double ymax = max(y1, max(y2, y3));

	for (double y = ymin; y < ymax; y++) {
		int offset = ((int)y)*W;
		for (double x = xmin; x < xmax; x++) {
			if ( (x*N1x + y*N1y <= D1) && (x*N2x + y*N2y <= D2) && (x*N3x + y*N3y <= D3) ) {
				mask[offset + (int)x] = TRUE;
			}
		}
	}
}

//Return a WxH mask representing where the face actually resides in the color/depth images (assuming the color/depth images
//have the same resolution)
HRESULT getFaceMask(BOOL* mask, IFTModel* pModel, FT_CAMERA_CONFIG const* pCameraConfig, FLOAT const* pSUCoef,
	FLOAT zoomFactor, POINT viewOffset, IFTResult* pAAMRlt)
{
	if (!mask || !pModel || !pCameraConfig || !pSUCoef || !pAAMRlt)
	{
		return E_POINTER;
	}
	int W = pCameraConfig->Width;
	int H = pCameraConfig->Height;
	for (int i = 0; i < H; i++) {
		for (int j = 0; j < W; j++){
			mask[i*W + j] = FALSE;
		}
	}

	HRESULT hr = S_OK;
	UINT vertexCount = pModel->GetVertexCount();
	FT_VECTOR2D* pPts2D = reinterpret_cast<FT_VECTOR2D*>(_malloca(sizeof(FT_VECTOR2D)* vertexCount));
	if (pPts2D)
	{
		FLOAT *pAUs;
		UINT auCount;
		hr = pAAMRlt->GetAUCoefficients(&pAUs, &auCount);
		if (SUCCEEDED(hr))
		{
			FLOAT scale, rotationXYZ[3], translationXYZ[3];
			hr = pAAMRlt->Get3DPose(&scale, rotationXYZ, translationXYZ);
			if (SUCCEEDED(hr))
			{
				hr = pModel->GetProjectedShape(pCameraConfig, zoomFactor, viewOffset, pSUCoef, pModel->GetSUCount(), pAUs, auCount,
					scale, rotationXYZ, translationXYZ, pPts2D, vertexCount);
				if (SUCCEEDED(hr))
				{
					POINT* p3DMdl = reinterpret_cast<POINT*>(_malloca(sizeof(POINT)* vertexCount));
					if (p3DMdl)
					{
						for (UINT i = 0; i < vertexCount; ++i)
						{
							p3DMdl[i].x = LONG(pPts2D[i].x + 0.5f);
							p3DMdl[i].y = LONG(pPts2D[i].y + 0.5f);
						}

						FT_TRIANGLE* pTriangles;
						UINT triangleCount;
						hr = pModel->GetTriangles(&pTriangles, &triangleCount);
						if (SUCCEEDED(hr))
						{
							for (UINT i = 0; i < triangleCount; i++) {
								POINT* P1 = &p3DMdl[pTriangles[i].i];
								POINT* P2 = &p3DMdl[pTriangles[i].j];
								POINT* P3 = &p3DMdl[pTriangles[i].k];
								fillTriangle(mask, W, H, P1, P2, P3);
							}
						}
						_freea(p3DMdl);
					}
					else
					{
						hr = E_OUTOFMEMORY;
					}
				}
			}
		}
		_freea(pPts2D);
	}
	else
	{
		hr = E_OUTOFMEMORY;
	}
	return hr;
}
