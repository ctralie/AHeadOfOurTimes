X = imread('NotreDameFrontHalfIDX.png');
X = double(X);
Y = X(:, :, 1)*(2^16) + X(:, :, 2)*(2^8) + X(:, :, 3);
Y(Y==50451) = 0;
%imagesc(Y);
%hold on;

[I, J] = meshgrid(1:size(Y, 2), 1:size(Y, 1));
I = I(Y > 0);
J = J(Y > 0);
Y = Y(Y > 0);
%plot(X(:, 1), X(:, 2), 'g.');
DT = delaunayTriangulation([I(:) J(:)]);

CX = imread('CandidePointsVirtue.png');
CX = double(CX(:, :, 1));

[I, J] = meshgrid(1:size(CX, 2), 1:size(CX, 1));
I = I(CX < 255);
J = J(CX < 255);
CX = CX(CX < 255 & CX > 0);
idx = CX - min(CX(:)) + 1;

N = length(unique(idx));
Pos = zeros(N, 2);
for ii = 1:N
    %Use the mean position
    IMean = mean(I(idx == ii));
    JMean = mean(J(idx == ii));
    Pos(ii, :) = [IMean JMean];
end
MeshIdx = Y(DT.nearestNeighbor(Pos));
[vertex, faces] = read_mesh('candide.off');
VerticesUsed = unique(faces(:));
load('NotreDameFrontHalfVerts.mat');
vertex(:, VerticesUsed) = NotreDameFrontHalfVerts(MeshIdx, :)';
plot_mesh(vertex, faces);