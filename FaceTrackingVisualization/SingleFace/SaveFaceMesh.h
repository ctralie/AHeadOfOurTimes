#pragma once

void saveFaceMesh(IFTImage* colorImage, NUI_IMAGE_RESOLUTION colorRes,
	IFTImage* depthImage, NUI_IMAGE_RESOLUTION depthRes, BOOL* faceMask);