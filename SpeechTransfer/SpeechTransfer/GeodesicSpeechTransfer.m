addpath(genpath('ShapeLAB'));
addpath(genpath('toolbox_fast_marching'));

TestName = 'BasicExample';
N = 300;
NoseUIdx = [26, 103, 6, 104, 51, 50, 85, 86, 84, 25, 26];
Border = [1 36 37 39 54 53 55 57 10 32 30 28 29 14 12 11];

plotlimsme = [];
winfudge = 0.02;
GSigma = 6;%Used to control geodesic distance falloff for interpolation

%Load in information about candide model and the Notre Dame statue
load('StatueInfo.mat');
MeshIdx = MeshIdx+1;
%Change candide model to only use faces that are incident on 
%vertices
[VCandide, FCandide] = read_mesh('candide.off');
uidx = unique(FCandide(:)); %Vertices actually used in the face

[VNotre, FNotre, CNotre] = readColorOff('NotreDameFrontHalf.off');
plotlimss = [min(VNotre(1, MeshIdx)), max(VNotre(1, MeshIdx)), ...
    min(VNotre(2, MeshIdx)), max(VNotre(2, MeshIdx)), ...
    min(VNotre(3, MeshIdx)), max(VNotre(3, MeshIdx))];

%Extract cropped region around the keypoints on the notre dame mesh
if ~exist('NotreCrop.mat')
    [VNotreCrop, FNotreCrop, cropmask, cropreindex] = ...
        extractFaceBoundary( VNotre, FNotre, Border, NoseUIdx, MeshIdx );
    save('NotreCrop.mat', 'VNotreCrop', 'FNotreCrop', 'cropmask', 'cropreindex');
else
    load('NotreCrop.mat');
end

kidx = cropreindex(MeshIdx);

%Setup normal and tangential coordinate systems on the first frame
%of the cropped Notre Dame statue
%Reference point used to make tangent (average of nose points)
RP = mean(VNotreCrop(:, kidx(NoseUIdx)), 2); 
[NormNotre, TanNotre, CrossNotre] = estimateNormalsTangents(VNotreCrop', FNotreCrop', RP);

%Compute geodesic distance to landmarks to be used for interpolation of
%change in normals, tangents, and cross displacements
if ~exist('NotreKeypointsGeodesics.mat')
    disp('Computing geodesics');
    DInterp = zeros(size(VNotreCrop, 2), length(MeshIdx));
    options.nb_iter_max = inf;
    for ii = 1:length(MeshIdx)
        ii
        DInterp(:, ii) = perform_fast_marching_mesh(VNotreCrop, FNotreCrop, cropreindex(MeshIdx(ii)), options)';   
    end
    DInterp = exp(-DInterp.^2/(GSigma^2));
    DInterp = bsxfun(@times, 1./sum(DInterp, 2), DInterp);
    save('NotreKeypointsGeodesics.mat', 'DInterp');
else
    load('NotreKeypointsGeodesics.mat');
end
%"Regularize" the normal/tangential/cross coordinates with geodesic
%interpolation
NormNotre = DInterp*NormNotre(kidx, :);
TanNotre = DInterp*TanNotre(kidx, :);
CrossNotre = DInterp*CrossNotre(kidx, :);

NotreShape.TRIV = FNotreCrop';
NotreShape.X = VNotreCrop(1, :)';
NotreShape.Y = VNotreCrop(2, :)';
NotreShape.Z = VNotreCrop(3, :)';

firstV = [];
for ii = 1:N
    %Step 1: Load in the vertices for the current frame of the video
    fin = fopen(sprintf('%s/%i.txt', TestName, ii-1), 'r');
    VMine = textscan(fin, '%f', 'delimiter', ' ');
    VMine = reshape(VMine{1}(2:end), [3, 121])';
    VMine(:, 3) = -VMine(:, 3); %Make right-handed coordinate system
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
        RP = mean(VMine(uidx(NoseUIdx), :), 1);
        %Estimate normals and tangents for first frame of my face
        [NormMe, TanMe, CrossMe] = estimateNormalsTangents(VMine, FCandide', RP);
        continue;
    end
    
    %Step 2: Perform the best rigid alignment possible to the first frame
    fprintf(1, 'Error Before ICP: %g\n', sum(sum((firstV(uidx, :) - VMine(uidx, :)).^2)));
    T = getRigidTransformation(VMine(uidx, :), firstV(uidx, :));
    VNew = [VMine ones(size(VMine, 1), 1)];
    VNew = T*VNew';
    VNew = VNew(1:3, :)';
    fprintf(1, 'Error After ICP: %g\n\n', sum(sum((firstV(uidx, :) - VNew(uidx, :)).^2)));
    
    subplot(1, 2, 1);
    plot_mesh(VNew, FCandide);
    xlim(plotlimsme(1:2));    ylim(plotlimsme(3:4));    zlim(plotlimsme(5:6));
    title('Original');
    
    %Step 3: Express displacements from the first frame as tangential,
    %normal, and cross displacements based on the chosen coordinate system
    %and transfer onto the local coordinate system of the statue mesh with
    %geodesic interoplation
    dV = VNew - firstV;
    dVNorm = dot(dV, NormMe, 2);    dVNorm = DInterp*dVNorm(uidx);
    dVTan = dot(dV, TanMe, 2);  dVTan = DInterp*dVTan(uidx);
    dVCross = dot(dV, CrossMe, 2);  dVCross = DInterp*dVCross(uidx);
    
    %Move keypoints
    V = VNotreCrop' + bsxfun(@times, dVNorm*1000, NormNotre) + ...
        bsxfun(@times, dVTan*1000, TanNotre) + bsxfun(@times, dVCross*1000, CrossNotre);
    
    subplot(1, 2, 2);
    plot_mesh(V', FNotreCrop);
    shading interp;
    title('Transformed');
    print('-dpng', '-r100', sprintf('%i.png', ii));
end
