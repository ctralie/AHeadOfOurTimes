%https://www.ceremade.dauphine.fr/~peyre/teaching/manifold/tp3.html
addpath('toolbox_fast_marching');
addpath('toolbox_fast_marching/toolbox');
addpath('toolbox_fast_marching/data');

filename = 'StyrofoamHead.off';
fileout = 'StyrofoamHead.toff';
landmarks = [3965, 2060, 3937, 370, 4172, 6055, 6056, 4201, 4191, 3969, 3960, 4179, 2274, 2285, 6088, 6061, 172, 157, 5795, 2032, 3930, 3936, 2030, 5808, 5802, 5814, 190, 182, 5806, 2044, 371, 380, 2043, 5835, 5832, 5846, 2078, 2088, 2102, 2109, 5892, 245, 5898, 2121, 5886, 3990, 2089, 2079, 6169, 467, 458, 462, 463, 4287, 2378, 2388, 2386, 6202, 6190, 6186, 6174, 4282, 475, 472, 4299, 4306, 4293, 4304, 2255, 2572, 2588, 6654, 6681, 2903, 6703, 4525, 2683, 2698, 2695, 708, 6704, 4732, 900, 6657, 621, 4454, 589, 4174, 4196, 3808, 160, 126, 5788, 2012, 353, 167, 169, 5798, 2022, 358];
landmarks = landmarks + 1;%Matlab indexing
NLandmarks = length(landmarks);

[vertex, faces] = read_mesh(filename);
NVertices = size(vertex, 2);    
[D, Z, Q] = perform_fast_marching_mesh(vertex, faces, landmarks);
[B, ~, J] = unique(Q);

v = randperm(NLandmarks)';
J(J == 101) = 100;
J = v(J);
clf;
hold on;
options.face_vertex_color = J;
plot_mesh(vertex, faces, options);
shading interp;
colormap jet(256);
h = plot3(vertex(1, landmarks), vertex(2, landmarks), vertex(3, landmarks), 'k.');
set(h, 'MarkerSize', 15);

keypoints = load('keypoints.txt');
keypoints = [keypoints(1:2:end)' keypoints(2:2:end)'];
tris = delaunay(keypoints(:, 1), keypoints(:, 2));
for ii = 1:size(tris, 1)
   endpoints = [tris(ii, :) tris(ii, 1)];
   endpoints = landmarks(endpoints);
   plot3(vertex(1, endpoints), vertex(2, endpoints), vertex(3, endpoints));
end

DLandmarks = zeros(NVertices, NLandmarks);
for ii = 1:NLandmarks
   [d, S, Q] = perform_fast_marching_mesh(vertex, faces, landmarks(ii)); 
   DLandmarks(:, ii) = d(:).^2;
   ii
end

size(DLandmarks)

% perform isomap on the reduced set of points
D1 = DLandmarks(landmarks,:); % reduced pairwise distances
D1 = (D1+D1')/2; % force symmetry
J = eye(NLandmarks) - ones(NLandmarks)/NLandmarks; % centering matrix
K = -1/2 * J*D1*J; % inner product matrix

% compute the rank-2 approximation of the inner product to compute embedding
opt.disp = 0;
[xy, val] = eigs(K, 2, 'LR', opt);
xy = xy .* repmat(1./sqrt(diag(val))', [NLandmarks 1]);% interpolation on the full set of points

% extend the embedding using geodesic interpolation
BadIdx = [1676, 1683];
KeepIdx = ones(1, NVertices);
KeepIdx(BadIdx) = 0;
KeepIdx = logical(KeepIdx);
DLandmarks = DLandmarks(KeepIdx, :);
NVertices = size(DLandmarks, 1);
textureCoords = zeros(NVertices,2);
deltan = mean(DLandmarks,1);
for x=1:NVertices
    deltax = DLandmarks(x,:);
    textureCoords(x,:) = 1/2 * ( xy' * ( deltan-deltax )' )';
end
textureCoords(KeepIdx, :) = textureCoords;


%Scale to the range [0, 1]
minTC = min(textureCoords, [], 1);
TC = textureCoords - repmat(minTC, size(textureCoords, 1), 1);
maxTC = max(TC, [], 1);
TC = TC./repmat(maxTC, size(textureCoords, 1), 1);

figure;
scatter(TC(landmarks, 1), TC(landmarks, 2), 100);
hold on;
plot(TC(:, 1), TC(:, 2), 'r.');
axis equal;

%Write texture coordinates to mesh file
fout = fopen(fileout, 'w');
fprintf(fout, 'TOFF picture.png\n');
fprintf(fout, '%i %i 0\n', size(vertex, 2), size(faces, 2));
for ii = 1:size(vertex, 2)
   fprintf(fout, '%g %g %g %g %g\n', vertex(1, ii), vertex(2, ii), vertex(3, ii), TC(ii, 1), TC(ii, 2)); 
end
for ii = 1:size(faces, 2)
   fprintf(fout, '3 %i %i %i\n', faces(1, ii) - 1, faces(2, ii) - 1, faces(3, ii) - 1); 
end
fclose(fout);

%Write locations of face vertices to a .mat file to use for warping another
%face
landmarksTC = TC(landmarks, :);
save('landmarksTC.mat', 'landmarksTC');


%vertex1 = vertex1';
% scatter(xy(:, 1), xy(:, 2))
% hold on;
% plot(vertex1(:, 1), vertex1(:, 2), 'r.');
% figure;
% plot_mesh(vertex1, faces);
% hold on;
% 
% h = plot3(vertex1(1, landmarks), vertex1(2, landmarks), vertex1(3, landmarks), 'r.');
% set(h, 'MarkerSize', 15);


