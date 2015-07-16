function [] = plotNormalsTansMesh( V, F, N, T, scale )
    addpath(genpath('../toolbox_fast_marching'));
    plot_mesh(V', F');
    hold on;
    scatter3(V(:, 1), V(:, 2), V(:, 3), 20, 'r', 'fill');
    for ii = 1:size(V, 1)
        P = [V(ii, :); V(ii, :) + scale*N(ii, :)];
        plot3(P(:, 1), P(:, 2), P(:, 3), 'b');
        P = [V(ii, :); V(ii, :) + scale*T(ii, :)];
        plot3(P(:, 1), P(:, 2), P(:, 3), 'g');
    end
end

