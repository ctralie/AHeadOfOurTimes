#pragma once

void saveFaceMesh(IFTImage* colorImage, NUI_IMAGE_RESOLUTION colorRes,
	IFTImage* depthImage, NUI_IMAGE_RESOLUTION depthRes, BOOL* faceMask);

void saveFaceMeshTempFile(IFTImage* colorImage, NUI_IMAGE_RESOLUTION colorRes,
	IFTImage* depthImage, NUI_IMAGE_RESOLUTION depthRes, BOOL* faceMask, float* rotation);

void getHeadCentroid(IFTImage* depthImage, NUI_IMAGE_RESOLUTION depthRes, BOOL* faceMask, FLOAT* cx, FLOAT* cy, FLOAT* cz);