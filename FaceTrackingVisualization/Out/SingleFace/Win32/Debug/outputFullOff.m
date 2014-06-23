temp;
X = squeeze(XYZ(:, :, 1));
Y = squeeze(XYZ(:, :, 2));
Z = squeeze(XYZ(:, :, 3));
R = squeeze(RGB(:, :, 1));
G = squeeze(RGB(:, :, 2));
B = squeeze(RGB(:, :, 3));

N = 640*480;
X = reshape(X, [N, 1]);
Y = reshape(Y, [N, 1]);
Z = reshape(Z, [N, 1]);
R = reshape(R, [N, 1]);
G = reshape(G, [N, 1]);
B = reshape(B, [N, 1]);
idx = (Z ~= 0);
X = X(idx); Y = Y(idx); Z = Z(idx);
R = R(idx); G = G(idx); B = B(idx);
NPoints = sum(idx);
Points = [X Y Z];
rotation(2) = rotation(2) + 180;%Coordinate system is left-handed by default
rotation = rotation*(pi/180);
Tx = rotation(1); Ty = rotation(2); Tz = rotation(3);
Rz = [cos(Tz) -sin(Tz) 0; ...
      sin(Tz) cos(Tz) 0; ...
      0 0 1];
Ry = [cos(Ty) 0 -sin(Ty); ...
      0 1 0; ...
      sin(Ty) 0 cos(Ty)];
Rx = [1 0 0; ...
      0 cos(Tx) -sin(Tx);...
      0 sin(Tx) cos(Tx)];
Points = Rz*Ry*Rx*Points';
Points = Points';
X = Points(:, 1); Y = Points(:, 2); Z = Points(:, 3);

offFile = fopen('out.off', 'w');
fprintf(offFile, 'COFF\n');
fprintf(offFile, '%i 0 0\n', NPoints);
for ii = 1:NPoints
    fprintf(offFile, '%g %g %g %i %i %i\n', X(ii), Y(ii), Z(ii), R(ii), G(ii), B(ii));
end
fclose(offFile);