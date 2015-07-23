%N x 3 verts, M x 3 faces
function [] = writeOff( filename, V, F )
    fout = fopen(filename, 'w');
    fprintf(fout, 'OFF\n');
    N = size(V, 1);
    M = size(F, 1);
    F = F - 1; %Matlab is 1-indexed
    fprintf(fout, '%i %i 0\n', N, M);
    for ii = 1:N
        fprintf(fout, '%g %g %g\n', V(ii, 1), V(ii, 2), V(ii, 3));
    end
    for ii = 1:M
        fprintf(fout, '3 %i %i %i\n', F(ii, 1), F(ii, 2), F(ii, 3));
    end
    fclose(fout);
end

