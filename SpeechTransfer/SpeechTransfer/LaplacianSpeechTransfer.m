TestName = 'BasicExample';
NFrames = 300;

addpath(genpath('ShapeLab'));
addpath(genpath('toolbox_fast_marching'));

NoseUIdx = [26, 103, 6, 104, 51, 50, 85, 86, 84, 25, 26];
Border = [1 36 37 39 54 53 55 57 10 32 30 28 29 14 12 11];

plotlimsme = [];
winfudge = 0.02;

%% Step 1: Load in and setup information about candide model and the Notre Dame statue
load('StatueInfo.mat');
MeshIdx = MeshIdx+1;
%Change candide model to only use faces that are incident on 
%vertices
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

[VNotre, FNotre, CNotre] = readColorOff('NotreDameFrontHalfMouthCut.off');
VNotreFirst(:, uidx) = VNotre(:, MeshIdx);
plotlimss = [min(VNotre(1, MeshIdx)), max(VNotre(1, MeshIdx)), ...
    min(VNotre(2, MeshIdx)), max(VNotre(2, MeshIdx)), ...
    min(VNotre(3, MeshIdx)), max(VNotre(3, MeshIdx))];

%% Step 2:Setup normal and tangential coordinate systems on the first frame
%of the Notre Dame statue
%Reference point used to make tangent (average of nose points)
RP = mean(VNotre(:, MeshIdx(NoseUIdx)), 2); 
[NormNotre, TanNotre, CrossNotre] = estimateNormalsTangents(VNotre(:, MeshIdx)', FCandide', RP);

%% Step 3: Setup Laplacian matrix for the cropped region of the face
NotreShape.TRIV = FNotre';
NotreShape.X = VNotre(1, :)';
NotreShape.Y = VNotre(2, :)';
NotreShape.Z = VNotre(3, :)';

MeshIdx = double(MeshIdx);
I = MeshIdx;
J = (1:length(MeshIdx))';
S = ones(length(MeshIdx), 1);
NotreShape.funcs = full(sparse(I, J, S, size(VNotre, 2), length(MeshIdx)));

L = mshlp_matrix(NotreShape,struct('dtype','cotangent'));
L = L + 300*speye(size(L, 1)); %Smooth out
% L = -1*(abs(L) > 0);
% L(1:size(L, 1)+1:end) = 0;
% diag = sum(L, 2);
% L(1:size(L, 1)+1:end) = abs(diag);

DeltaCoords = L*VNotre';
%Add anchor entries
[I, J, S] = find(L);

omega = 1;
nrange = MeshIdx;
N = length(nrange);
I = [I; size(L, 1) + (1:N)'];
J = [J; nrange(:)];
S = [S; omega*ones(N, 1)];
DeltaCoords = [DeltaCoords; omega*VNotre(:, 1:N)'];
L = sparse(I, J, S, size(L, 1)+N, size(L, 2));
A = L'*L;
%http://www.mathworks.com/help/matlab/examples/sparse-matrices.html#zmw57dd0e2472
p = symamd(A); %Reorder to reduce fill
pback(p) = 1:length(p); %Inverse permutation
disp('Doing cholesky factorization...');
R = chol(A(p, p), 'lower');
disp('Finished cholesky factorization');

%% Step 4: Loop through each frame and do the deformation
firstV = [];
for ii = 1:NFrames
    %Step 1: Load in the vertices for the current frame of the video
    fin = fopen(sprintf('%s/%i.txt', TestName, ii-1), 'r');
    VMine = textscan(fin, '%f', 'delimiter', ' ');
    VMine = reshape(VMine{1}(2:end), [3, 121])';
    VMine(:, 3) = -VMine(:, 3); %Make right-handed coordinate system
    VMine = VMine(uidx, :);
    fclose(fin);
    if isempty(plotlimsme)
        plotlimsme = [min(VMine(:, 1)) - winfudge, max(VMine(:, 1)) + winfudge, ...
            min(VMine(:, 2)) - winfudge, max(VMine(:, 2)) + winfudge, ...
            min(VMine(:, 3)) - winfudge, max(VMine(:, 3)) + winfudge];
    end
    clf;
    if ii == 1
        plot_mesh(VMine', FCandide');
        firstV = VMine;
        RP = mean(VMine(NoseUIdx, :), 1);
        %Estimate normals and tangents for first frame of my face
        [NormMe, TanMe, CrossMe] = estimateNormalsTangents(VMine, FCandide', RP);        
        continue;
    end
    
%     if exist(sprintf('%i.png', ii))
%         continue;
%     end
    
    %Step 2: Perform the best rigid alignment possible to the first frame
    fprintf(1, 'Error Before ICP: %g\n', sum(sum((firstV - VMine).^2)));
    T = getRigidTransformation(VMine, firstV);
    VNew = [VMine ones(size(VMine, 1), 1)];
    VNew = T*VNew';
    VNew = VNew(1:3, :)';
    fprintf(1, 'Error After ICP: %g\n\n', sum(sum((firstV - VNew).^2)));
    
    subplot(1, 3, 1);
    plot_mesh(VNew', FCandide);
    xlim(plotlimsme(1:2));    ylim(plotlimsme(3:4));    zlim(plotlimsme(5:6));
    title('Original');
    
    %Step 3: Express displacements from the first frame as tangential,
    %normal, and cross displacements based on the chosen coordinate system
    %and transfer onto the local coordinate system of the statue mesh with
    %geodesic interoplation.  Then use laplacian mesh with these new points
    %as anchors
    dV = VNew - firstV;
    dVNorm = dot(dV, NormMe, 2);
    dVTan = dot(dV, TanMe, 2);
    dVCross = dot(dV, CrossMe, 2);
    
    %Move keypoints
    VAnchors = VNotreFirst(:, uidx)' + bsxfun(@times, dVNorm*1000, NormNotre) + ...
        bsxfun(@times, dVTan*1000, TanNotre) + bsxfun(@times, dVCross*1000, CrossNotre);
    subplot(1, 3, 2);
    plot_mesh(VAnchors', FCandide);
    title('Anchors');
    
    %Apply keypoints as anchors
    DeltaCoords(end-size(VAnchors, 1)+1:end, :) = omega*VAnchors;
    Y = L'*DeltaCoords;
    tic
    VNotreNew = R\(R'\Y(p, :));
    toc
    VNotreNew = VNotreNew(pback, :);
    
    subplot(1, 3, 3);
    clf;
    plot_mesh(VNotreNew', FNotre);
    hold on;
    scatter3(VAnchors(:, 1), VAnchors(:, 2), VAnchors(:, 3), 10, 'r', 'full');
    shading interp;
    title('Transformed');
    set(gcf,'PaperUnits','inches','PaperPosition',[0 0 18 6])
    print('-dpng', '-r100', sprintf('%i.png', ii));
    fprintf(1, 'Finished Frame %i\n', ii);
end