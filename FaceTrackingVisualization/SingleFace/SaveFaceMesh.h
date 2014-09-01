#pragma once

void saveFaceImageWithKeypoints(IFTImage* colorImage, NUI_IMAGE_RESOLUTION colorRes,
	FT_VECTOR2D* keyPoints, UINT NPoints);

void saveFaceMesh(IFTImage* colorImage, NUI_IMAGE_RESOLUTION colorRes,
	IFTImage* depthImage, NUI_IMAGE_RESOLUTION depthRes, BOOL* faceMask);

void saveFaceMeshTempFile(IFTImage* colorImage, NUI_IMAGE_RESOLUTION colorRes,
	IFTImage* depthImage, NUI_IMAGE_RESOLUTION depthRes, BOOL* faceMask, float* rotation);

void getHeadCentroid(IFTImage* depthImage, NUI_IMAGE_RESOLUTION depthRes, BOOL* faceMask, FLOAT* cx, FLOAT* cy, FLOAT* cz);