addpath(genpath('toolbox_fast_marching'));
X = imread('NotreDameFrontHalfIDX.png');
X = uint32(X);
Y = X(:, :, 1)*(2^16) + X(:, :, 2)*(2^8) + X(:, :, 3);
Y(Y==max(Y(:))) = 0;
%imagesc(Y);
%hold on;

[I, J] = meshgrid(1:size(Y, 2), 1:size(Y, 1));
I = I(Y > 0);
J = J(Y > 0);
Y = Y(Y > 0);
uniqueY = unique(Y);
uniqueI = zeros(size(uniqueY));
uniqueJ = zeros(size(uniqueY));
N = length(uniqueY);
%SUPER SLOW WAY BELOW!
for ii = 1:N
    idxs = find(Y == uniqueY(ii));
    uniqueI(ii) = mean(I(idxs));
    uniqueJ(ii) = mean(J(idxs));
end
I = uniqueI;
J = uniqueJ;
addpath(genpath('toolbox_fast_marching'));
Y = uniqueY;
PosStatue = [I(:) J(:)];

CX = imread('CandidePointsVirtue.png');
CX = double(CX(:, :, 1));

[I, J] = meshgrid(1:size(CX, 2), 1:size(CX, 1));
I = I(CX < 255);
J = J(CX < 255);
CX = CX(CX < 255 & CX > 0);
idx = CX - min(CX(:)) + 1;

N = length(unique(idx));
PosCandide = zeros(N, 2);
for ii = 1:N
    %Use the mean position
    IMean = mean(I(idx == ii));
    JMean = mean(J(idx == ii));
    PosCandide(ii, :) = [IMean JMean];
end

D = pdist2(PosCandide, PosStatue);
MeshIdx = ones(length(PosCandide), 1);
for ii = 1:length(PosCandide)
    [~, idx] = min(D(ii, :));
    MeshIdx(ii) = Y(idx);
    D(:, idx) = Inf;
end

[VCandide, FCandide] = read_mesh('candide.off');
uidx = unique(FCandide(:)); %Vertices actually used in the face
usedv = zeros(1, size(VCandide, 2));
usedv(uidx) = 1;
usedf = usedv(FCandide);
FCandide = FCandide(:, sum(usedf, 1) == 3);
reindex = zeros(1, size(VCandide, 2));
reindex(uidx) = 1:length(uidx);
FCandide = reindex(FCandide);
VCandide = VCandide(:, uidx);

[verts, faces] = readColorOff('NotreDameFrontHalfMouthCut.off');
plot_mesh(verts(:, MeshIdx), FCandide);

MeshIdx = MeshIdx - 1;
save('StatueInfo.mat', 'MeshIdx');