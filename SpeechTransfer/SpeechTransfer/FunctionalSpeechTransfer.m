DRAWBASIS = 1;
TESTFUNCTIONS = 1;

addpath(genpath('ShapeLab'));
addpath(genpath('toolbox_fast_marching'));

TestName = 'BasicExample';
N = 300;
NoseUIdx = [26, 103, 6, 104, 51, 50, 85, 86, 84, 25, 26];
Border = [1 36 37 39 54 53 55 57 10 32 30 28 29 14 12 11];

plotlimsme = [];
winfudge = 0.02;
NBasis = 30; %Number of functions in the Laplace-Beltrami Basis

%Load in information about candide model and the Notre Dame statue
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
[~, FCandide] = read_mesh('candidesolid.off');

[VNotre, FNotre] = readColorOff('NotreDameFrontHalf.off');
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

%Setup normal and tangential coordinate systems on the first frame
%of the cropped Notre Dame statue
%Reference point used to make tangent (average of nose points)
RP = mean(VNotreCrop(:, cropreindex(MeshIdx(NoseUIdx))), 2); 
[NormNotre, TanNotre, CrossNotre] = estimateNormalsTangents(VNotreCrop', FNotreCrop', RP);

%Setup Discrete Laplace Beltrami Matrix for the cropped region on the
%statue face
NotreShape.TRIV = FNotreCrop';
NotreShape.X = VNotreCrop(1, :)';
NotreShape.Y = VNotreCrop(2, :)';
NotreShape.Z = VNotreCrop(3, :)';
[NotreShape.basis, ~, NotreShape.areas] = calcLaplacianBasis(NotreShape, NBasis);
I = cropreindex(MeshIdx)';
J = (1:length(MeshIdx))';
S = ones(length(MeshIdx), 1);
NotreShape.funcs = full(sparse(I, J, S, size(VNotreCrop, 2), length(MeshIdx)));

if DRAWBASIS
    %Output pictures of laplace beltrami eigenfunctions
    fout = fopen('ShapeEigs.html', 'w');
    fprintf(fout, '<html>\n<body><table>');
    for ii = 1:size(NotreShape.basis, 2)
        drawShape(NotreShape, NotreShape.basis(:, ii));
        view(0, 90);
        print('-dpng', '-r100', sprintf('NotreBasis%i.png', ii));
        fprintf(fout, '<tr><td><h1>%i</h1><td><img src = "NotreBasis%i.png"></td><td><img src = "MyBasis%i.png"></td></tr>\n', ii, ii, ii);
    end
    fprintf(fout, '</body></html>');
    fclose(fout);
end

firstV = [];
MyShape = [];
C = []; %Functional Map
for ii = 1:1%N
    %Step 1: Load in the vertices for the current frame of the video
    fin = fopen(sprintf('%s/%i.txt', TestName, ii-1), 'r');
    VMine = textscan(fin, '%f', 'delimiter', ' ');
    VMine = reshape(VMine{1}(2:end), [3, 121])';
    VMine(:, 3) = -VMine(:, 3); %Make right-handed coordinate system
    VMine = VMine(uidx, :); %Only extract vertices that are being used
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
        MyShape = struct();
        MyShape.X = VMine(:, 1);
        MyShape.Y = VMine(:, 2);
        MyShape.Z = VMine(:, 3);
        MyShape.TRIV = FCandide';
        MyShape.funcs = eye(size(VMine, 1));
        [W, A] = mshlp_matrix(MyShape,struct('dtype','cotangent'));
        [MyShape.basis, ~, MyShape.areas] = calcLaplacianBasis(MyShape, NBasis);
        if DRAWBASIS
            for kk = 1:size(NotreShape.basis, 2)
                drawShape(MyShape, MyShape.basis(:, kk));
                view(0, 90);
                print('-dpng', '-r100', sprintf('MyBasis%i.png', kk));
            end
        end
        %Calculate functional map
        C = calcCFromFuncsAndStructure(MyShape, NotreShape, MyShape.funcs, NotreShape.funcs, ...
            'basis1', MyShape.basis, 'areas1', MyShape.areas, 'basis2', NotreShape.basis, 'areas2', NotreShape.areas);
        if TESTFUNCTIONS
            for kk = 1:size(VMine, 1)
                f = zeros(size(VMine, 1), 1);
                f(kk) = 1;
                fnotre = NotreShape.basis*C*(MyShape.basis)'*f;
                subplot(1, 2, 1);
                drawShape(MyShape, f);
                view(0, 90);
                subplot(1, 2, 2);
                drawShape(NotreShape, fnotre);
                view(0, 90);
                print('-dpng', '-r100', sprintf('%iTestFn.png', kk));
            end
        end
        
        RP = mean(VMine(NoseUIdx, :), 1);
        %Estimate normals and tangents for first frame of my face
        [NormMe, TanMe, CrossMe] = estimateNormalsTangents(VMine, FCandide', RP);
        continue;
    end
    
    %Step 2: Perform the best rigid alignment possible to the first frame
    fprintf(1, 'Error Before ICP: %g\n', sum(sum((firstV - VMine).^2)));
    T = getRigidTransformation(VMine, firstV);
    VNew = [VMine ones(size(VMine, 1), 1)];
    VNew = T*VNew';
    VNew = VNew(1:3, :)';
    fprintf(1, 'Error After ICP: %g\n\n', sum(sum((firstV - VNew).^2)));
    
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
    
    
end
