%http://www.mathworks.com/help/imaq/examples/using-the-kinect-r-for-windows-r-from-image-acquisition-toolbox-tm.html
%http://www.mathworks.com/help/imaq/logging-image-data-to-disk.html
%"The depth map is distance in millimeters from the camera plane"

if 0
%%
utilpath = fullfile(matlabroot, 'toolbox', 'imaq', 'imaqdemos', ...
    'html', 'KinectForWindows');
addpath(utilpath);
hwInfo = imaqhwinfo('kinect');

colorVid = videoinput('kinect', 1);
depthVid = videoinput('kinect', 2);

triggerconfig([colorVid depthVid],'manual');

FramesToAcquire = 300;
colorVid.FramesPerTrigger = FramesToAcquire;
depthVid.FramesPerTrigger = FramesToAcquire;

logfileColor = VideoWriter('logfile.avi');
colorVid.LoggingMode = 'disk&memory';
colorVid.DiskLogger = logfileColor;

logfileDepth = VideoWriter('logfiledepth.mj2', 'Motion JPEG 2000');
depthVid.LoggingMode = 'disk&memory';
depthVid.DiskLogger = logfileDepth;

Fs = 22050;
audioRecObj = audiorecorder(Fs, 16, 1);

MaxFrames = 5*60*30;
colorVid.FramesAcquiredFcnCount = 1;
colorVid.FramesAcquiredFcn = {KinectCaptureCallbacks(1, MaxFrames, audioRecObj)};
depthVid.FramesAcquiredFcnCount = 1;
depthVid.FramesAcquiredFcn = {KinectCaptureCallbacks(1, MaxFrames, audioRecObj)};


record(audioRecObj);
start([colorVid depthVid]);
trigger([colorVid depthVid]);

while colorVid.FramesAcquired ~= FramesToAcquire || depthVid.FramesAcquired ~= FramesToAcquire
    pause(0.1);
end
stop(audioRecObj);

X = getaudiodata(audioRecObj);

colorTimes = colorVid.UserData;
colorTimes = colorTimes(1:colorVid.FramesAcquired, :);
depthTimes = depthVid.UserData;
depthTimes = depthTimes(1:depthVid.FramesAcquired, :);
save('frameTimes.mat', 'colorTimes', 'depthTimes');
audiowrite('audio.ogg', X, Fs);
disp('Finish capture and logging to disk');
end

if 1
%%
clear all;
%Track and plot face keypoints
depthVid = videoinput('kinect', 2);
depthReader = VideoReader('logfiledepth.mj2');
colorReader = VideoReader('logfile.avi');
disp('Initializing tracker...');
[DM,TM,options] = xx_initialize;
frame_w = 640;
frame_h = 480;

%Get the elapsed seconds relative to the first color frame
load('frameTimes.mat');
colorAudioSamples = colorTimes(:, end);
colorTimesDT = datetime(fix(colorTimes(:, 1:6)));
colorTimes = seconds(colorTimesDT - colorTimesDT(1)) + (colorTimes(:, 6) - floor(colorTimes(:, 6)));
depthAudioSamples = depthTimes(:, end);
depthTimesDT = datetime(fix(depthTimes(:, 1:6)));
depthTimes = seconds(depthTimesDT - colorTimesDT(1)) + (depthTimes(:, 6) - floor(depthTimes(:, 6)));

output.pred = [];% prediction set to null enabling detection
depthFrameNum = 1;
TRI = [];
for depthFrameNum = 1:length(depthTimes)
    clf;
    depthFrame = read(depthReader, depthFrameNum);
    %Find the color frame with the closest timestamp
    [~, colorFrameNum] = min(abs(colorTimes - depthTimes(depthFrameNum)));
    colorFrame = read(colorReader, colorFrameNum);
    dims = size(colorFrame);
    
    fprintf(1, 'depthFrameNum = %i, colorFrameNum = %i\n', depthFrameNum, colorFrameNum);
    
    alignedColorImage = alignColorToDepth(depthFrame, colorFrame, depthVid);
    output = xx_track_detect(DM,TM,alignedColorImage,output.pred,options);
    
    if isempty(output.pred)
        continue;
    end
    
    keyPoints = output.pred;
    if isempty(TRI)
        TRI = delaunay(double(keyPoints));
    end
    
    xyzPoints = depthToPointCloud(depthFrame, depthVid);
    keyPoints = int32(round(keyPoints));
    FacePC = zeros(size(keyPoints, 1), 3);
    for ii = 1:length(keyPoints)
        FacePC(ii, :) = xyzPoints(keyPoints(ii, 2), keyPoints(ii, 1), :);
    end
    h34 = subplot(2, 2, 3:4);
    cla(h34);
    trimesh(TRI, FacePC(:, 1), FacePC(:, 2), FacePC(:, 3));
    hold on;
    plot3(FacePC(:, 1), FacePC(:, 2), FacePC(:, 3), 'r.');
    view(0, -50);
    axis equal;
    axis off;
    
    wBorder = 15;
    subplot(2, 2, 2);
    depthFrame = fliplr(depthFrame);
    imagesc(depthFrame);
    axis equal;
    hold on;
    scatter(keyPoints(:, 1), keyPoints(:, 2), 4, 'g', 'fill');
    xlim([min(keyPoints(:, 1)) - wBorder, max(keyPoints(:, 1)) + wBorder]);
    ylim([min(keyPoints(:, 2)) - wBorder, max(keyPoints(:, 2)) + wBorder]);
    title(sprintf('%i', depthFrameNum));
    keyPointsIdx = sub2ind(dims, keyPoints(:, 2), keyPoints(:, 1));
    clims = [min(depthFrame(keyPointsIdx)), max(depthFrame(keyPointsIdx))];
    caxis(clims);
    colorbar;
    
    subplot(2, 2, 1);
    imagesc(alignedColorImage);
    axis equal;
    hold on;
    scatter(keyPoints(:, 1), keyPoints(:, 2), 4, 'g', 'fill');
    xlim([min(keyPoints(:, 1)) - wBorder, max(keyPoints(:, 1)) + wBorder]);
    ylim([min(keyPoints(:, 2)) - wBorder, max(keyPoints(:, 2)) + wBorder]);
    title(sprintf('%i', colorFrameNum));    

    print('-dpng', '-r200', sprintf('%i.png', depthFrameNum));
end
end