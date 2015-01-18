%http://www.mathworks.com/help/imaq/examples/using-the-kinect-r-for-windows-r-from-image-acquisition-toolbox-tm.html
%http://www.mathworks.com/help/imaq/logging-image-data-to-disk.html
%"The depth map is distance in millimeters from the camera plane"

if 1
%%
utilpath = fullfile(matlabroot, 'toolbox', 'imaq', 'imaqdemos', ...
    'html', 'KinectForWindows');
addpath(utilpath);
hwInfo = imaqhwinfo('kinect');

colorVid = videoinput('kinect', 1);
depthVid = videoinput('kinect', 2);

triggerconfig([colorVid depthVid],'manual');

FramesToAcquire = 60;
colorVid.FramesPerTrigger = FramesToAcquire;
depthVid.FramesPerTrigger = FramesToAcquire;

logfileColor = VideoWriter('logfile.avi');
colorVid.LoggingMode = 'disk&memory';
colorVid.DiskLogger = logfileColor;

logfileDepth = VideoWriter('logfiledepth.mj2', 'Motion JPEG 2000');
depthVid.LoggingMode = 'disk&memory';
depthVid.DiskLogger = logfileDepth;

audioRecObj = audiorecorder(22050, 16, 1);

MaxFrames = 5*60*30;
colorVid.FramesAcquiredFcnCount = 1;
colorVid.FramesAcquiredFcn = {KinectCaptureCallbacks(1, MaxFrames, audioRecObj)};
depthVid.FramesAcquiredFcnCount = 1;
depthVid.FramesAcquiredFcn = {KinectCaptureCallbacks(1, MaxFrames, audioRecObj)};


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
end

if 0
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
colorTimesDT = datetime(fix(colorTimes));
colorTimes = seconds(colorTimesDT - colorTimesDT(1, :)) + (colorTimes(:, end) - floor(colorTimes(:, end)));
depthTimesDT = datetime(fix(depthTimes));
depthTimes = seconds(depthTimesDT - colorTimesDT(1, :)) + (depthTimes(:, end) - floor(depthTimes(:, end)));

output.pred = [];% prediction set to null enabling detection
depthFrameNum = 1;
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
    
    subplot(2, 2, 1);
    imagesc(colorFrame);
    title(sprintf('%i', colorFrameNum));
    axis equal;
    subplot(2, 2, 2);
    imagesc(depthFrame);
    title(sprintf('%i', depthFrameNum));
    axis equal;
    
    subplot(2, 2, 4);
    imagesc(fliplr(depthFrame));
    hold on;
    scatter(output.pred(:, 1), output.pred(:, 2), 10, 'g', 'fill');
    axis equal;

    subplot(2, 2, 3);
    imagesc(alignedColorImage);
    hold on;
    scatter(output.pred(:, 1), output.pred(:, 2), 10, 'g', 'fill');
    axis equal;

%     xyzPoints = depthToPointCloud(depthFrame, depthVid);
%     X = xyzPoints(:, :, 1);
%     Y = xyzPoints(:, :, 2);
%     Z = xyzPoints(:, :, 3);
%     C = double(reshape(alignedColorImage, [], 3)) / 255.0;
%     scatter3(X(:), Y(:), Z(:), 20, reshape(alignedColorImage, [], 3), '.');

    print('-dpng', '-r200', sprintf('%i.png', depthFrameNum));
end
end