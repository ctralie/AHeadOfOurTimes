function [VNotreMask, FNotreMask, mask, vreindex] = extractFaceBoundary( VNotre, FNotre, Border, NoseUIdx, MeshIdx )
    disp('Extracting face boundary...');
    options.v2v = compute_vertex_ring(FNotre);
    options.e2f = compute_edge_face_ring(FNotre);
    options.method = 'discrete';
    options.verb = 0;
    vboundary = [];
    vidx = MeshIdx(Border);
    for ii = 1:length(Border)
        ii
        D = perform_fast_marching_mesh(VNotre, FNotre, vidx(ii));
        nextii = ii+1;
        if nextii > length(Border)
            nextii = 1;
        end
        [~, nextv] = compute_geodesic_mesh(D, VNotre, FNotre, vidx(nextii), options);
        vboundary = [vboundary nextv];
    end
    
    %It's horrible to have to do depth first search in Matlab but here goes
    %Using java linked list to make things hopefully a little faster
    mask = zeros(1, size(VNotre, 2));
    startv = MeshIdx(NoseUIdx(1));
    mask(startv) = 1;
    mask(vboundary) = 2;
    v2v = options.v2v;
    q = java.util.LinkedList;
    neighbs = v2v{startv};
    for ii = 1:length(neighbs)
        q.push(neighbs(ii));
    end
    while q.size() > 0
        v = q.removeLast();
        if (mask(v) > 0)
            continue;
        end
        mask(v) = 1;
        neighbs = v2v{v};
        for ii = 1:length(neighbs)
            q.push(neighbs(ii));
        end
    end
    mask = mask > 0;
    vreindex = 1:length(mask);
    vreindex(mask) = 1:sum(mask);
    VNotreMask = VNotre(:, mask);
    FaceMask = mask(FNotre);
    FaceMask = sum(FaceMask, 1) == 3;
    FNotreMask = vreindex(FNotre(:, FaceMask));
end

