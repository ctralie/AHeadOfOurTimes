% res = 800;
% 
% %X1: The original face image
% %X1 = load('keypoints.txt');
% %X1 = [X1(1:2:end)' X1(2:2:end)'];
% %imagein = imread('face.png');
% 
% X1 = load('MyFaceKeypoints.txt');
% imagein = imread('MyFace.jpg');
% 
% %X2: The target texture coordinate landmarks
% X2 = load('landmarksTC.mat');
% X2 = X2.landmarksTC;
% 
% X2 = X2*res;%Scale coords to fit inside of output image cube
% imageout = 100*ones(res, res, 3);
% 
% %Use D2's delaunay triangulation class for fast point
% %location, and impose the graph topology of D2 on X1
% D2 = delaunayTriangulation(X2);
% 
% %Perform point location inside of delaunay grid for each triangle
% [X, Y] = meshgrid(1:res, 1:res);
% X = X(:); Y = Y(:);
% X2Grid = [X Y];
% idx = D2.pointLocation(X2Grid);
% 
% %Compute barycentric coordinates of each point inside the
% %corresponding triangle
% 
% %validCoords holds the indices where points actually fall in one
% %of the delaunay triangles
% validCoords = 1:length(idx);
% validCoords = validCoords(~isnan(idx));
% 
% a1 = D2.Points(D2.ConnectivityList(idx(validCoords), 1), :);
% a2 = D2.Points(D2.ConnectivityList(idx(validCoords), 2), :);
% a3 = D2.Points(D2.ConnectivityList(idx(validCoords), 3), :);
% x = X2Grid(validCoords, :);
% 
% lam1 = (a2(:, 2) - a3(:, 2)).*(x(:, 1) - a3(:, 1)) + (a3(:, 1) - a2(:, 1)).*(x(:, 2) - a3(:, 2));
% lam1 = lam1./( (a2(:, 2) - a3(:, 2)).*(a1(:, 1) - a3(:, 1)) + (a3(:, 1) - a2(:, 1)).*(a1(:, 2) - a3(:, 2)) );
% 
% lam2 = (a3(:, 2) - a1(:, 2)).*(x(:, 1) - a3(:, 1)) + (a1(:, 1) - a3(:, 1)).*(x(:, 2) - a3(:, 2));
% lam2 = lam2./( (a2(:, 2) - a3(:, 2)).*(a1(:, 1) - a3(:, 1)) + (a3(:, 1) - a2(:, 1)).*(a1(:, 2) - a3(:, 2)));
% 
% lam3 = 1 - lam1 - lam2;
% 
% %Use the barycentric coordinates to go back to X1 to find the points
% %Impose the graph topology of D2 on X1 so that they have the same triangles
% b1 = X1(D2.ConnectivityList(idx(validCoords), 1), :);
% b2 = X1(D2.ConnectivityList(idx(validCoords), 2), :);
% b3 = X1(D2.ConnectivityList(idx(validCoords), 3), :);
% gridCenter = repmat(lam1, 1, 2).*b1 + repmat(lam2, 1, 2).*b2 + repmat(lam3, 1, 2).*b3;
% 
% %Do nearest neighbor for now (TODO: Improve interpolation)
% gridCenter = round(gridCenter);
% for ii = 1:size(gridCenter, 1)
%    %I have to use the transpose of the input image and rotate
%    %the output image by 90 degrees for some reason
%    imageout(size(imageout, 1) - x(ii, 2), x(ii, 1), :) = imagein(gridCenter(ii, 2), gridCenter(ii, 1), :);
% end
% imageout = imageout/max(imageout(:))*255.0;
% imageout = uint8(imageout);
% imagesc(imageout);
% imwrite(imageout, 'picture.png');

figure;
imagesc(imagein);
hold on;
for triIndex = 1:size(D2, 1)
   tri = D2(triIndex, :);
   for ii = 1:3
       i1 = ii;
       i2 = ii+1;
       if ii == 3
          i2 = 1; 
       end
       plot([X1(tri(i1), 1), X1(tri(i2), 1)], [X1(tri(i1), 2), X1(tri(i2), 2)], 'b');
   end
end
axis equal;

figure;
imagesc(imageout);
hold on;
for triIndex = 1:size(D2, 1)
   tri = D2(triIndex, :);
   for ii = 1:3
       i1 = ii;
       i2 = ii+1;
       if ii == 3
          i2 = 1; 
       end
       plot([X2(tri(i1), 1), X2(tri(i2), 1)], res - [X2(tri(i1), 2), X2(tri(i2), 2)], 'b');
   end
end
axis equal;