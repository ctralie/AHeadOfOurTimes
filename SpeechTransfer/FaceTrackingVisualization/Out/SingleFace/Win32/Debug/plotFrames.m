for ii = 0:89
   X = load(sprintf('%i.txt', ii));
   timestamp = X(1);
   X = X(2:end, :);
   plot3(X(:, 1), X(:, 2), X(:, 3), '.');
   view(168, -88);
   pause(0.1);
end