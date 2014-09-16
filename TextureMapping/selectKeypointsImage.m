image = imread('MyFace.jpg');
keypoints = zeros(100, 2);
numberStrings = cellstr(num2str((0:size(keypoints, 1)-1)'));

imagesc(image);
hold on;
for ii = 1:14
   keypoints(ii, :) = ginput(1);
   plot(keypoints(ii, 1), keypoints(ii, 2), '.');
   text(keypoints(ii, 1), keypoints(ii, 2), numberStrings(ii));
end