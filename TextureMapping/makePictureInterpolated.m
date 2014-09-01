%Given the texture coordinates and some landmarks, do a warping to create
%the picture
keypoints = load('keypoints.txt');
keypoints = [keypoints(1:2:end)' keypoints(2:2:end)'];
tris = delaunay(keypoints(:, 1), keypoints(:, 2));
load('landmarksTC.mat');
image = imread('face.png');