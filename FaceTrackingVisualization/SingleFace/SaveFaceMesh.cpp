#include <stdafx.h>
#include <FaceTrackLib.h>
#include <fstream>
#include <iostream>
#include <math.h>
#include <NuiApi.h>
#include "FTHelper.h"

using namespace std;

void saveFaceMesh(IFTImage* colorImage, NUI_IMAGE_RESOLUTION colorRes, 
	IFTImage* depthImage, NUI_IMAGE_RESOLUTION depthRes, BOOL* faceMask) {
	int iWidth = depthImage->GetWidth();
	int iHeight = depthImage->GetHeight();

	BYTE* depthImageBuffer = depthImage->GetBuffer();
	BYTE* colorImageBuffer = colorImage->GetBuffer();
	//Initialize array that stores the index of each vertex
	int N = 0;
	LONG* vertexIndices = new LONG[iWidth*iHeight];
	for (int y = 0; y < iHeight; y++) {
		int offset = y*iWidth;
		for (int x = 0; x < iWidth; x++) {
			int index = offset + x;
			USHORT* ptr = (USHORT*)(depthImageBuffer + 2 * index);
			if (faceMask[index] && *ptr > 0) {
				vertexIndices[index] = N;
				N++;
			}
			else {
				vertexIndices[index] = -1;
			}
		}
	}


	ofstream offFile;
	offFile.open("C:\\Users\\ctralie\\Desktop\\out.off");
	offFile << "OFF\n";
	offFile << N << " 0 0\n";
	ofstream plyFile;
	plyFile.open("C:\\Users\\ctralie\\Desktop\\out.ply");
	plyFile << "ply\n";
	plyFile << "format ascii 1.0\n";
	plyFile << "element vertex " << N << "\n";
	plyFile << "property float x\nproperty float y\nproperty float z\n";
	plyFile << "property uchar red\nproperty uchar green\nproperty uchar blue\nproperty uchar alpha\n";
	plyFile << "end_header\n";

	for (int y = 0; y < iHeight; y++) {
		int offset = y*iWidth;
		for (int x = 0; x < iWidth; x++) {
			USHORT* ptr = (USHORT*)(depthImageBuffer + 2 * (offset + x));
			if (!faceMask[offset + x] || *ptr == 0)
				continue;
			USHORT usDepthValue = *ptr;
			Vector4 P = NuiTransformDepthImageToSkeleton(x, y, usDepthValue, depthRes);//This doesn't work
			LONG plColorX, plColorY;
			NuiImageGetColorPixelCoordinatesFromDepthPixelAtResolution(colorRes, depthRes, NULL, x, y, usDepthValue, &plColorX, &plColorY);
			LONG index = plColorX + plColorY*iWidth;
			BYTE B = colorImageBuffer[index * 4];
			BYTE G = colorImageBuffer[index * 4 + 1];
			BYTE R = colorImageBuffer[index * 4 + 2];
			BYTE A = colorImageBuffer[index * 4 + 3];
			//FLOAT Z = (FLOAT)(usDepthValue/1000.0f);
			//TODO: This assumes the depth camera center is the center of the image
			//FLOAT X = (FLOAT)(x - W / 2)*Z/f;
			//FLOAT Y = (FLOAT)(y - H / 2)*Z/f;
			FLOAT X = P.x / P.w;
			FLOAT Y = P.y / P.w;
			FLOAT Z = P.z / P.w;
			//FLOAT X = (x - iWidth / 2) / 320.0f;
			//FLOAT Y = (y - iHeight / 2) / 240.0f;
			//FLOAT Z = ((FLOAT)usDepthValue) / 1000.0f;
			offFile << X << " " << Y << " " << Z << " " << (float)R / 255.0 << " " << (float)G / 255.0 << " " << (float)B / 255.0 << (float)A / 255.0 << "\n";
			plyFile << X << " " << Y << " " << Z << " " << (int)R << " " << (int)G << " " << (int)B << " " << (int)A << "\n";
		}
	}
	offFile.close();
	plyFile.close();
	delete[] vertexIndices;
}