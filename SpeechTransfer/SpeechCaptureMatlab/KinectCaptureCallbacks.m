function [c] = KinectCaptureCallbacks(type, arg1, arg2)
    frameCounter = 1;
    FrameTimes = [];
    
    function frameTimesCallback( obj, event, MaxFrames, audioRecObj )
        if isempty(obj.UserData)
            FrameTimes = zeros(MaxFrames, 7);
        end
        FrameTimes(frameCounter, 1:6) = event.Data.AbsTime;
        FrameTimes(frameCounter, 7) = audioRecObj.TotalSamples;
        frameCounter = frameCounter + 1;
        %TODO: Hacky solution (but timing is negligible)
        obj.UserData = FrameTimes;
    end

    if type == 1
        c = @(obj, event) frameTimesCallback(obj, event, arg1, arg2);
    end
end