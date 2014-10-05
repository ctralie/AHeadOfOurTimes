%https://www.ceremade.dauphine.fr/~peyre/teaching/manifold/tp3.html
addpath('toolbox_fast_marching');
addpath('toolbox_fast_marching/toolbox');
addpath('toolbox_fast_marching/data');

%Styrofoam Head
%filename = 'StyrofoamHead.off';
%fileout = 'StyrofoamHead.toff';
%landmarks = [3965, 2060, 3937, 370, 4172, 6055, 6056, 4201, 4191, 3969, 3960, 4179, 2274, 2285, 6088, 6061, 172, 157, 5795, 2032, 3930, 3936, 2030, 5808, 5802, 5814, 190, 182, 5806, 2044, 371, 380, 2043, 5835, 5832, 5846, 2078, 2088, 2102, 2109, 5892, 245, 5898, 2121, 5886, 3990, 2089, 2079, 6169, 467, 458, 462, 463, 4287, 2378, 2388, 2386, 6202, 6190, 6186, 6174, 4282, 475, 472, 4299, 4306, 4293, 4304, 2255, 2572, 2588, 6654, 6681, 2903, 6703, 4525, 2683, 2698, 2695, 708, 6704, 4732, 900, 6657, 621, 4454, 589, 4174, 4196, 3808, 160, 126, 5788, 2012, 353, 167, 169, 5798, 2022, 358];
%[vertex, faces] = read_mesh(filename);

%Statue Head
%filename = 'NotreDameDownsampled.off';
%fileout = 'NotreDame.toff';
%landmarks = [2330, 2332, 2200, 8164, 1500, 1632, 1852, 2020, 3176, 8629, 6606, 6127, 6189, 5948, 5786, 3313, 8505, 8471, 2624, 2359, 2156, 8151, 2202, 2477, 2569, 2620, 8604, 5836, 3562, 8687, 6334, 6245, 3654, 4047, 8658, 8603, 2671, 2530, 2232, 6942, 4432, 1946, 2117, 5086, 8368, 8484, 2715, 5388, 773, 1248, 1466, 8073, 4449, 5003, 2353, 2088, 1795, 1523, 1304, 1024, 7974, 1489, 1770, 3935, 2103, 2013, 6578, 1414, 1267, 4124, 381, 209, 64, 4165, 4178, 236, 4198, 687, 1268, 1715, 5010, 3969, 3022, 5710, 5784, 3602, 3761, 2036, 5834, 2230, 3070, 2974, 8517, 8421, 8324, 3299, 8661, 6107, 4635, 3793];
filename = 'NotreDameFrontHalf.off';
fileout = 'NotreDameFrontHalf.toff';
landmarks = [44371, 8572, 8241, 43624, 6269, 20252, 7423, 8023, 11179, 45610, 45878, 25513, 13646, 25105, 12053, 20830, 44979, 9933, 9720, 8821, 20419, 43672, 8325, 9028, 9507, 9617, 45664, 13056, 25857, 26316, 26465, 14191, 13570, 46108, 20974, 45552, 9893, 44516, 8649, 43720, 43716, 8081, 8471, 44346, 44755, 23634, 9927, 10654, 4562, 5602, 6319, 7119, 20403, 23113, 20568, 8390, 7449, 6588, 5782, 5259, 42910, 6540, 7251, 7808, 18517, 7375, 6790, 6017, 5941, 3634, 41131, 40466, 40031, 1292, 40529, 2251, 41681, 4177, 5635, 22659, 23155, 23662, 10900, 12320, 25235, 25795, 26672, 7693, 30861, 8521, 20772, 10793, 20722, 44676, 8692, 11818, 46095, 14250, 26664, 15165];
[vertex, faces] = readColorOff(filename);

landmarks = landmarks + 1;%Matlab indexing
NLandmarks = length(landmarks);


NVertices = size(vertex, 2);    
[D, Z, Q] = perform_fast_marching_mesh(vertex, faces, landmarks);
[B, ~, J] = unique(Q);
options.method = 'continuous';
options.verb = 0;
paths = compute_geodesic_mesh(D, vertex, faces, landmarks, options);
optionx.colorfx;
plot_fast_marching_mesh(vertex, faces, D, paths, options);

% v = randperm(NLandmarks)';
% J(J == 101) = 100;
% J = v(J);
% clf;
% hold on;
% options.face_vertex_color = D;
% plot_mesh(vertex, faces, options);
% shading interp;
% colormap jet(256);
% h = plot3(vertex(1, landmarks), vertex(2, landmarks), vertex(3, landmarks), 'k.');
% set(h, 'MarkerSize', 15);

keypoints = load('keypoints.txt');
keypoints = [keypoints(1:2:end)' keypoints(2:2:end)'];
tris = delaunay(keypoints(:, 1), keypoints(:, 2));
for ii = 1:size(tris, 1)
   endpoints = [tris(ii, :) tris(ii, 1)];
   endpoints = landmarks(endpoints);
   plot3(vertex(1, endpoints), vertex(2, endpoints), vertex(3, endpoints));
end

DLandmarks = zeros(NVertices, NLandmarks);
parfor ii = 1:NLandmarks
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
BadIdx = logical(isinf(DLandmarks(:, 1)));
KeepIdx = ones(1, NVertices);
KeepIdx(BadIdx) = 0;
KeepIdx = logical(KeepIdx);
DLandmarks = DLandmarks(KeepIdx, :);
NVertices = size(DLandmarks, 1);
textureCoords = zeros(NVertices,2);
deltan = mean(DLandmarks,1);
parfor x=1:NVertices
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
plot(TC(1:20:end, 1), TC(1:20:end, 2), 'r.');
hold on;
scatter(TC(landmarks, 1), TC(landmarks, 2), 10);
axis square;
axis equal;

%Write texture coordinates to mesh file
fout = fopen(fileout, 'w');
fprintf(fout, 'TOFF picture.png\n');
fprintf(fout, '%i %i 0\n', size(vertex, 2), size(faces, 2));
disp('Writing vertices...');
for ii = 1:size(vertex, 2)
   fprintf(fout, '%g %g %g %g %g\n', vertex(1, ii), vertex(2, ii), vertex(3, ii), TC(ii, 1), TC(ii, 2));
   if mod(ii, 1000) == 0
      fprintf(1, '.'); 
   end
   if mod(ii, 20000) == 0
       fprintf(1, '\n');
   end
end
disp('Writing faces...');
for ii = 1:size(faces, 2)
   fprintf(fout, '3 %i %i %i\n', faces(1, ii) - 1, faces(2, ii) - 1, faces(3, ii) - 1);
   if mod(ii, 1000) == 0
      fprintf(1, '.'); 
   end
   if mod(ii, 20000) == 0
       fprintf(1, '\n');
   end
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


