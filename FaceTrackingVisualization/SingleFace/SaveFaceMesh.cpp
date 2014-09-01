#include <stdafx.h>
#include <FaceTrackLib.h>
#include <fstream>
#include <iostream>
#include <math.h>
#include <NuiApi.h>
#include "FTHelper.h"
#include "SaveFaceMesh.h"
#include "CImg.h"
using namespace cimg_library;

using namespace std;

void saveFaceImageWithKeypoints(IFTImage* colorImage, NUI_IMAGE_RESOLUTION colorRes,
	FT_VECTOR2D* keyPoints, UINT NPoints) {
	int iWidth = colorImage->GetWidth();
	int iHeight = colorImage->GetHeight();
	BYTE* colorImageBuffer = colorImage->GetBuffer();
	CImg<unsigned char> image(iWidth, iHeight, 1, 3, 0);

	for (int y = 0; y < iHeight; y++) {
		int offset = y*iWidth;
		for (int x = 0; x < iWidth; x++) {
			LONG index = x + y*iWidth;
			BYTE B = colorImageBuffer[index * 4];
			BYTE G = colorImageBuffer[index * 4 + 1];
			BYTE R = colorImageBuffer[index * 4 + 2];
			BYTE A = colorImageBuffer[index * 4 + 3];
			unsigned char color[3] = { R, G, B };
			image.draw_rectangle(x, y, x + 1, y + 1, color);
		}
	}
	unsigned char c_blue[3] = { 0, 0, 255 };
	ofstream keyPointsFile;
	keyPointsFile.open("keypoints.txt");
	for (int i = 0; i < NPoints; i++) {
		int x = (int)keyPoints[i].x;
		int y = (int)keyPoints[i].y;
		//image.draw_rectangle(x, y, x + 2, y + 2, c_blue);
		keyPointsFile << keyPoints[i].x << " " << keyPoints[i].y << " ";
	}
	image.save("face.png");
}



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
			Vector4 P = NuiTransformDepthImageToSkeleton(x, y, usDepthValue, depthRes);
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


void saveFaceMeshTempFile(IFTImage* colorImage, NUI_IMAGE_RESOLUTION colorRes,
	IFTImage* depthImage, NUI_IMAGE_RESOLUTION depthRes, BOOL* faceMask, float* rotation) {
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

	ofstream tempFile;
	tempFile.open("temp.txt");
	//Also save the color and the depth image as a .m file
	ofstream colorDepthStream;
	colorDepthStream.open("temp.m");
	colorDepthStream << "xyzrgb = [";
	for (int y = 0; y < iHeight; y++) {
		int offset = y*iWidth;
		for (int x = 0; x < iWidth; x++) {
			USHORT* ptr = (USHORT*)(depthImageBuffer + 2 * (offset + x));
			USHORT usDepthValue = *ptr;
			Vector4 P = NuiTransformDepthImageToSkeleton(x, y, usDepthValue, depthRes);
			LONG plColorX, plColorY;
			NuiImageGetColorPixelCoordinatesFromDepthPixelAtResolution(colorRes, depthRes, NULL, x, y, usDepthValue, &plColorX, &plColorY);
			LONG index = plColorX + plColorY*iWidth;
			BYTE B  = 0, G = 0, R = 0, A = 0;
			if (index * 4 < iWidth*iHeight * 4) {
				B = colorImageBuffer[index * 4];
				G = colorImageBuffer[index * 4 + 1];
				R = colorImageBuffer[index * 4 + 2];
				A = colorImageBuffer[index * 4 + 3];
			}
			FLOAT X = P.x / P.w;
			FLOAT Y = P.y / P.w;
			FLOAT Z = P.z / P.w;
			colorDepthStream << X << " " << Y << " " << Z << " " << (int)R << " " << (int)G << " " << (int)B << ";\n";
			if (!faceMask[offset + x] || *ptr == 0)
				continue;//Only output the point if it's within the face mask
			tempFile << y << " " << x << " " << X << " " << Y << " " << Z << " " << (int)R << " " << (int)G << " " << (int)B << "\n";
		}
	}
	tempFile.close();
	colorDepthStream << "];\n";
	colorDepthStream << "RGB = reshape(xyzrgb(:, 4:6), 640, 480, 3);\n";
	colorDepthStream << "XYZ = reshape(xyzrgb(:, 1:3), 640, 480, 3);\n";
	colorDepthStream << "RGB = permute(uint8(RGB), [2, 1, 3]);\n";
	colorDepthStream << "XYZ = permute(XYZ, [2, 1, 3]);\n";
	colorDepthStream << "clear xyzrgb;\n";
	colorDepthStream << "rotation = [" << rotation[0] << " " << rotation[1] << " " << rotation[2] << "]\n";
	colorDepthStream.close();
	delete[] vertexIndices;
}


void getHeadCentroid(IFTImage* depthImage, NUI_IMAGE_RESOLUTION depthRes, BOOL* faceMask, FLOAT* cx, FLOAT* cy, FLOAT* cz) {
	int iWidth = depthImage->GetWidth();
	int iHeight = depthImage->GetHeight();

	BYTE* depthImageBuffer = depthImage->GetBuffer();
	//Initialize array that stores the index of each vertex
	int N = 0;
	for (int y = 0; y < iHeight; y++) {
		int offset = y*iWidth;
		for (int x = 0; x < iWidth; x++) {
			int index = offset + x;
			USHORT* ptr = (USHORT*)(depthImageBuffer + 2 * index);
			if (faceMask[index] && *ptr > 0) {
				N++;
			}
		}
	}

	*cx = 0;
	*cy = 0;
	*cz = 0;
	for (int y = 0; y < iHeight; y++) {
		int offset = y*iWidth;
		for (int x = 0; x < iWidth; x++) {
			USHORT* ptr = (USHORT*)(depthImageBuffer + 2 * (offset + x));
			if (!faceMask[offset + x] || *ptr == 0)
				continue;
			USHORT usDepthValue = *ptr;
			Vector4 P = NuiTransformDepthImageToSkeleton(x, y, usDepthValue, depthRes);
			FLOAT X = P.x / P.w;
			FLOAT Y = P.y / P.w;
			FLOAT Z = P.z / P.w;
			*cx = *cx + X;
			*cy = *cy + Y;
			*cz = *cz + Z;
		}
	}
	*cx = *cx / (FLOAT)N;
	*cy = *cy / (FLOAT)N;
	*cz = *cz / (FLOAT)N;
}