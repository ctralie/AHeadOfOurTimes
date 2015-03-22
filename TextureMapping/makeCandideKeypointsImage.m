%Make an image of the candide points that are connected to faces, with
%the color of the pixel in each image associated with different keypoints
%being slightly different
addpath('toolbox_fast_marching');
addpath('toolbox_fast_marching/toolbox');
addpath('toolbox_fast_marching/data');

[vertex, faces] = read_mesh('candide.off');
VerticesUsed = unique(faces(:));

% V = vertex';
% scatter3(V(VerticesUsed, 1), V(VerticesUsed, 2), V(VerticesUsed, 3), 20, 'b', 'fill');
% hold on;
% VerticesNotUsed = 1:size(V, 1);
% VerticesNotUsed(VerticesUsed) = 0;
% VerticesNotUsed = VerticesNotUsed(VerticesNotUsed > 0);
% scatter3(V(VerticesNotUsed, 1), V(VerticesNotUsed, 2), V(VerticesNotUsed, 3), 20, 'r', 'fill');
% axis off;

vertex = vertex(:, VerticesUsed);
for ii = 1:size(faces, 1)
    for jj = 1:size(faces, 2)
        faces(ii, jj) = find(VerticesUsed == faces(ii, jj), 1);
    end
end
options.nb_iter_max = Inf;
N = size(vertex, 2);
D = zeros(N, N);
for ii = 1:N
    D(ii, :) = perform_fast_marching_mesh(vertex, faces, ii, options);
end
idx = 1:N;
D = 0.5*(D + D');
Y = cmdscale(D(idx, idx));

W = 800;
H = 1000;
I = zeros(H, W, 3);
Y = bsxfun(@minus, Y, min(Y, [], 1));
Y = bsxfun(@times, Y, 1.0./max(Y, [], 1));
Y(:, 1) = Y(:, 1)*H*0.9 + 50;
Y(:, 2) = Y(:, 2)*W*0.9 + 50;
Y = round(Y);
%plot(A(:, 2), A(:, 1), '.');
dx = 1;
for ii = size(Y, 1):-1:1
    I(Y(ii, 1)+(-dx:dx), Y(ii, 2)+(-dx:dx), 1) = 150 + ii;
end
I = uint8(I);
I = flipud(I);
U = unique(I(:));
imwrite(I, 'CandidePoints.png');