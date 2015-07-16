%Estimate vertex normals as a weighted sum of their adjacent face normals
%Come up with tangents from the normals and a reference point
function [ N, T, C, FN, FA ] = estimateNormalsTangents( V, F, RP )
    %First compute the area and normal of each face
    FA = zeros(size(F, 1), 1);
    FN = zeros(size(F, 1), 3);
    for ii = 1:size(F, 1)
        Vs = V(F(ii, :), :);
        dV1 = Vs(2, :) - Vs(1, :);
        dV2 = Vs(3, :) - Vs(1, :);
        VN = cross(dV1, dV2);
        FA(ii) = 0.5*norm(VN);
        FN(ii, :) = VN/norm(VN);
    end
    
    %Now compute the vertex normals as weighted areas of the face normals
    N = zeros(size(V, 1), 3); 
    for ii = 1:size(V, 1)
        %NOTE: This is a *super inefficient version* thanks to Matlab's
        %lack of convenient data structures.  But should be OK for small
        %meshes
        adjF = 1:size(F, 1);
        adjF = adjF(sum(F == ii, 2) >= 1);
        if isempty(adjF)
            continue;
        end
        VN = zeros(1, 3);
        for kk = 1:length(adjF)
            VN = VN + FA(adjF(kk))*FN(adjF(kk), :);
        end
        N(ii, :) = VN/norm(VN);
    end
    T = bsxfun(@minus, V, RP(:)');
    T = T - bsxfun(@times, dot(T, N, 2), N);
    T = bsxfun(@times, 1./sqrt(sum(T.^2, 2)), T);
    C = cross(N, T);
end