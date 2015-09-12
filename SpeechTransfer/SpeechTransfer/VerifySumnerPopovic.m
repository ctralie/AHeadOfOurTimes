addpath(genpath('toolbox_fast_marching'));
[VCandide, FCandide] = read_mesh('candide.off');

TestName = 'BasicExample';
NFrames = 300;
for ii = 0:NFrames-1
    clf;
    fin = fopen(sprintf('%s/%i.txt', TestName, ii), 'r');
    VMine = textscan(fin, '%f', 'delimiter', ' ');
    VMine = reshape(VMine{1}(2:end), [3, 121])';
    VStatue = load(sprintf('%s/Statue%i.txt', TestName, ii));
    subplot(1, 2, 1);
    plot_mesh(VMine', FCandide);
    subplot(1, 2, 2);
    plot_mesh(VStatue', FCandide);
    print('-dpng', '-r100', sprintf('%i.png', ii));
end