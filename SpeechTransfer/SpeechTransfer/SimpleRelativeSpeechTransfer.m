addpath(genpath('ShapeLab'));
addpath(genpath('toolbox_fast_marching'));

TestName = 'BasicExample';
N = 300;
NoseUIdx = [26, 103, 6, 104, 51, 50, 85, 86, 84, 25, 26];

plotlimsme = [];
winfudge = 0.02;
NBasis = 30; %Number of functions in the Laplace-Beltrami Basis

%Load in information about candide statue
load('StatueInfo.mat');
MeshIdx = MeshIdx+1;
[VNotreFirst, FCandide] = read_mesh('candide.off');
uidx = unique(FCandide(:)); %Vertices actually used in the face

%Load in the subset of points on the notre dame statue that 
%correspond to the vertices on the candide statue
[VNotre, FNotre] = readColorOff('NotreDameFrontHalf.off');
VNotreFirst(:, uidx) = VNotre(:, MeshIdx);
plotlimss = [min(VNotre(1, uidx)), max(VNotre(1, uidx)), ...
    min(VNotre(2, uidx)), max(VNotre(2, uidx)), ...
    min(VNotre(3, uidx)), max(VNotre(3, uidx))];

%Setup normal and tangential coordinate systems on the first frame
%of the Notre Dame statue
%Reference point used to make tangent (average of nose points)
RP = mean(VNotreFirst(:, uidx(NoseUIdx)), 2); 
[NormNotre, TanNotre, CrossNotre] = estimateNormalsTangents(VNotreFirst', FCandide', RP);

%TODO: Setup the laplacian matrix for the full statue


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
    %and transfer onto the local coordinate system of the statue mesh
    dV = VNew - firstV;
    dVNorm = dot(dV, NormMe, 2);
    dVTan = dot(dV, TanMe, 2);
    dVCross = dot(dV, CrossMe, 2);
    
    V = VNotreFirst' + bsxfun(@times, dVNorm*1000, NormNotre) + ...
        bsxfun(@times, dVTan*1000, TanNotre) + bsxfun(@times, dVCross*1000, CrossNotre);
    V = inv(T)*[V ones(size(V, 1), 1)]';
    
    subplot(1, 2, 2);
    plot_mesh(V(1:3, :), FCandide);
    title('Transformed');
    print('-dpng', '-r100', sprintf('%i.png', ii));
end
