face = imread('face.png');
keypoints = load('keypoints.txt');
keypoints = [keypoints(1:2:end)' keypoints(2:2:end)'];

imshow(face);
hold on;
numberStrings = cellstr(num2str((0:size(keypoints, 1)-1)'));
idx = 80:90;
plot(keypoints(idx, 1), keypoints(idx, 2), 'r.');
text(keypoints(idx, 1), keypoints(idx, 2), numberStrings(idx));

tris = delaunay(keypoints(:, 1), keypoints(:, 2));
for ii = 1:size(tris, 1)
   idx = [tris(ii, :) tris(ii, 1)];
   plot(keypoints(idx, 1), keypoints(idx, 2));
end