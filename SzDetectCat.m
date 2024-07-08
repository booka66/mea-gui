function [DischargeTimes,SzTimes,DischargeTrainsTimes,SETimes] = SzDetectCat(V,sampRate,do_analysis)
if ~do_analysis
    DischargeTimes = [];
    SzTimes = [];
    DischargeTrainsTimes = [];
    SETimes = [];
    return
end
t = transpose(linspace(0,round(length(V)/round(sampRate)),length(V))); 
window_size = (round(sampRate));
step_size = (round(sampRate)/2);
num_steps = floor((length(t)-window_size)/step_size) + 1;
moving_var = nan(num_steps, 1);
tVar = nan(num_steps, 1); % Initialize tVar

idx = 1;
for w = window_size:step_size:length(t)
    % Extract window data
    window_data = V((w-window_size+1):w);
    
    % Calculate moving variance
    moving_var(idx) = var(window_data);
    
    % Store the corresponding time for the current window
    tVar(idx) = t(w); % Store the time value at the end of the window
    
    idx = idx + 1;
end

T = (1/round(sampRate))*length(V);
nsc = floor(length(V)/T);
nov = floor(nsc/2);
nff = max(256,2^nextpow2(nsc));
[S,~,T] = spectrogram(V,hamming(nsc),nov,nff,round(sampRate));
SP = sum(abs(S));

% Determine Reference section
% Check how long the V is in seconds
Refsize = 2; %min
TotRefCheck = 5; %min

% Set the window size
window_size = (round(sampRate)*60*Refsize);
VtoCheck = (round(sampRate)*60*TotRefCheck);

% Specify the step size for the window
step_size = (round(sampRate)/2); %.5sec

% Initialize
range = 1:step_size:(VtoCheck - window_size + 1);
min_dev_values = zeros(1, numel(range));

% Calculate deviation in each window
for i = 1:numel(range)
    end_index = range(i) + window_size - 1;

    % Check if the end index exceeds the size of V
    if end_index > numel(V)
        break;  % Exit the loop if the index is out of bounds
    end

    window_data = V(range(i):end_index);
    deviation = abs(window_data - mean(window_data));
    min_dev_values(i) = sum(deviation);
end

% Find the minimum value and its index
median_idx = ceil(length(min_dev_values)/2); %median group

% Store the reference section location
referenceIdxs = [range(median_idx), (range(median_idx) + window_size - 1)];

%Store the reference sections as unique lists
tRef = [t(referenceIdxs(1)),t(referenceIdxs(2))];
VRef = V(referenceIdxs(1):referenceIdxs(2));
varRef = moving_var(find(tVar>=tRef(1),1):find(tVar>=tRef(2),1));
FreqRef = SP(find(T>=tRef(1),1):find(T>=tRef(2),1));

%Remove outliers
Voutliers = isoutlier(VRef);
VRef = VRef(~Voutliers);

varoutliers = isoutlier(varRef);
varRef = varRef(~varoutliers);

Freqoutliers = isoutlier(FreqRef);
FreqRef = FreqRef(~Freqoutliers);

%Thresholds:
Vthresh = max(abs(VRef))*2.2;
Varthresh = max(varRef)*2;
Freqthresh = max(FreqRef)*1;

% Calculate the number of samples in the time window
window_length = 2; % Time window length in seconds
window_samples = round(window_length * round(sampRate));

% Initialize an array to store the peak counts
peak_counts = zeros(size(t));

% Calculate the step size (ensuring it's an integer)
step_size = floor(window_samples / 2);

warning('off', 'signal:findpeaks:largeMinPeakHeight');
for i = window_samples:step_size:length(t)-window_samples+1
    % Extract the current window
    window_start = i;
    window_end = i + window_samples - 1;
    window_data = V(window_start:window_end);
    
    % Find peaks in the current window
    [~, locs] = findpeaks(abs(window_data), 'MinPeakHeight', Vthresh);

    % Store the peak count for the current window
    peak_counts(i) = numel(locs); %#ok
end

VardownsampleRatio = length(T)/length(t);
Var_window_samples = round(window_length * (round(sampRate)*VardownsampleRatio));
Varpeak_counts = zeros(size(tVar));
step_size = 1;

for i = Var_window_samples:step_size:length(tVar)-Var_window_samples+1
    % Extract the current window
    window_start = i;
    window_end = i + Var_window_samples - 1;
    window_data = moving_var(window_start:window_end);
    
    % Find peaks in the current window
    [~, Varlocs] = findpeaks(window_data, 'MinPeakHeight', Varthresh);

    % Store the peak count for the current window
    Varpeak_counts(i) = numel(Varlocs); %#ok
end

FreqdownsampleRatio = length(T)/length(t);
Freq_window_samples = round(window_length * (round(sampRate)*FreqdownsampleRatio));
Freqpeak_counts = zeros(size(T));
step_size = 1;

for i = Freq_window_samples:step_size:length(T)-Freq_window_samples+1
    % Extract the current window
    window_start = i;
    window_end = i + Freq_window_samples - 1;
    window_data = SP(window_start:window_end);
    
    % Find peaks in the current window
    [~, Freqlocs] = findpeaks(window_data, 'MinPeakHeight', Freqthresh);

    % Store the peak count for the current window
    Freqpeak_counts(i) = numel(Freqlocs); %#ok
end
warning('on', 'signal:findpeaks:largeMinPeakHeight')

SameEventLimit = 5;
Vrolling_avg = movmean(peak_counts, round(sampRate)*SameEventLimit);
Varrolling_avg = movmean(Varpeak_counts, round(sampRate)*SameEventLimit*VardownsampleRatio);
Frolling_avg = movmean(Freqpeak_counts, round(sampRate)*SameEventLimit*FreqdownsampleRatio);

%Determine overlaps for peak zones
% Initialize the logical array with false values
discharge_list = false(size(t));


% Loop through the time vector t
for i = (round(sampRate)):length(t) %start from first second
    % Check if the current time in t is true for all three
    time_idx = t(i);
    Varidx = find(tVar>time_idx,1)-1;
    if isempty(Varidx)
        Varidx = length(tVar);
    end
    Freqidx = find(T>time_idx,1)-1;
    if isempty(Freqidx)
        Freqidx = length(T);
    end

    if Vrolling_avg(i) ~=0 && Varrolling_avg(Varidx) ~=0 && Frolling_avg(Freqidx) ~=0
        discharge_list(i) = true;
    end
end

%Parse out the 10sec Szs
LenLim = (round(sampRate))*10;

% Initialize the new logical list with false values
tenSecSz = false(size(t));

% Find the start and end indices of each sequence of true values
starts = find(diff([false; discharge_list(:)]) == 1);
ends = find(diff([discharge_list(:); false]) == -1);

% Loop through each sequence and check its length
for i = 1:length(starts)
    if (ends(i) - starts(i) + 1) >= LenLim
        % Preserve the true values for sequences that are at least LenLim long
        tenSecSz(starts(i):ends(i)) = true;
    end
end

SzStartIdxs = find(diff([false; tenSecSz(:)]) == 1);
SzEndIdxs = find(diff([false; [tenSecSz(:); 0]]) == -1);

%After a 15sec Sz, check for discharges after (and catch for SE)
LookAheadTime = 15;
SEList = false(size(t));
SEIdxLim = 300*round(sampRate); % 5 min (300sec)

if exist('SzWithTrain','var')
    clear("SzWithTrain")
end
for k = 1:length(SzStartIdxs)
    EventDur = (SzEndIdxs(k)-1)-SzStartIdxs(k);
    if EventDur>SEIdxLim %SE check
        SEList((SzEndIdxs(k)-1):SzStartIdxs(k)) = true;
    end
    checking = true;
    eventEnd = (SzEndIdxs(k)-1);
    spikeTrain = [];
    while checking == true
        nextidx = eventEnd+ (round(sampRate)*LookAheadTime);
        if nextidx > length(discharge_list)
            nextidx =  length(discharge_list);
        end

        if all(discharge_list(eventEnd:nextidx) ==0)
            checking = false;
        else
            spikeTrain = [spikeTrain discharge_list(eventEnd:nextidx)']; %#ok
            eventEnd = nextidx;
            if nextidx == length(discharge_list)
                checking = false;
            end
        end
    end
    SzWithTrain{k,1} = [tenSecSz(SzStartIdxs(k):(SzEndIdxs(k)-1))]; %#ok %Sz time 
    SzWithTrain{k,2} = spikeTrain'; %#ok %Trains
    SzWithTrain{k,3} = length(find(diff([spikeTrain]) == 1)); %#ok %Num of discharges
end

if ~exist('SzWithTrain', 'var')
    SzWithTrain = [];
end

%Add single discharges to Sz and categorize other trains
DischargeTrains = false(size(t));

for k = 1:size(SzWithTrain,1)
    Train = SzWithTrain{k,2};
    numDischarges = SzWithTrain{k,3};
    DischargeEnd = find(Train==1,1,'last');
    DischargeStart= find(Train==1,1,'first');
    if numDischarges == 1 % Append single discharges to Szs
        tenSecSz((SzEndIdxs(k)-1):((SzEndIdxs(k)-1)+DischargeEnd)) = true;
    elseif numDischarges > 1
        EventDur = (DischargeEnd+(SzEndIdxs(k)-1))-SzStartIdxs(k);
        if EventDur>SEIdxLim %If the Event len exceeds SE, length=>SE
            SEList(((SzEndIdxs(k)-1)+DischargeStart):((SzEndIdxs(k)-1)+DischargeEnd)) = true;
        else
            DischargeTrains(((SzEndIdxs(k)-1)+DischargeStart):((SzEndIdxs(k)-1)+DischargeEnd)) = true;
        end
    end
end

%Eliminate overlaps
try
    DischargeTrains(tenSecSz & DischargeTrains) = false; 
catch
    DischargeTrains = DischargeTrains(1:length(t));
    tenSecSz = tenSecSz(1:length(t));
    DischargeTrains(tenSecSz & DischargeTrains) = false; 
end
try
    tenSecSz(tenSecSz & SEList) = false;
catch
    SEList = SEList(1:length(t));
    tenSecSz(tenSecSz & SEList) = false;
end

%Catch the non-included discharges and assign them

dischargeStarts = find(diff([false; discharge_list(:)]) == 1);
dischargeEnds = find(diff([false; [discharge_list(:); 0]]) == -1);
CatchLim = 15*round(sampRate);

for k = 1:length(dischargeStarts)
    try
        LookBackTime = dischargeStarts(k) - CatchLim;
        SEList(LookBackTime);
    catch
        LookBackTime = 1;
    end
    if any(SEList(LookBackTime:dischargeStarts(k)))  %Grouping catch for SE
       SEList(LookBackTime:(dischargeEnds(k)-1)) = true;
    end
end

%Check backwards through the discharges to get any missing SE
ALL_Discharges = discharge_list | tenSecSz | DischargeTrains | SEList;
CatchLim = 15*round(sampRate); %15 sec groupo together limit
AllDischargeStarts = find(diff([false; ALL_Discharges(:)]) == 1);

for i = 1:length(AllDischargeStarts)
    startIdx = AllDischargeStarts(i);
    
    % Determine the range to check back
    if i == 1
        checkStart = max(1, startIdx - (CatchLim-1)); % Ensure not to go below index 1
    else
        previousStartIdx = AllDischargeStarts(i - 1);
        checkStart = max(previousStartIdx, startIdx - (CatchLim-1)); % Ensure not to overlap previous start index
    end
    
    % Check if any value in the range is true
    if any(ALL_Discharges(checkStart:startIdx - 1))
        markStart = max(1, startIdx - (CatchLim-1)); % Ensure not to go below index 1
        if markStart <=2
            markStart = 2;
        end
        ALL_Discharges((markStart-1):startIdx) = true;
    end
end

%Check for SE
AlldischargeStarts = find(diff([false; ALL_Discharges(:)]) == 1);
AlldischargeEnds = find(diff([false; [ALL_Discharges(:); 0]]) == -1);
SEList = false(size(t));
SETimeLim = SEIdxLim/sampRate;

for k = 1:size(AlldischargeStarts,1)
    DischargeEnd = AlldischargeEnds(k)-1;
    DischargeStart= AlldischargeStarts(k);
    EventDur = t(DischargeEnd)-t(DischargeStart);
    if EventDur>SETimeLim %If the Event len exceeds SE, length=>SE
        SEList((DischargeStart):(DischargeEnd)) = true;
    end
end

%%Eliminate in priority order
%Take out SE from other lists
discharge_list(SEList & discharge_list) = false;
DischargeTrains(SEList & DischargeTrains) = false;
tenSecSz(SEList & tenSecSz) = false;

%Take out Szs from lower lists
discharge_list(tenSecSz & discharge_list) = false;
DischargeTrains(tenSecSz & DischargeTrains) = false;

%Take out Trains from discharges
discharge_list(DischargeTrains & discharge_list) = false;

%%Remove any isolated small blips from discharges
% Find the start and end indices of consecutive true values
startIdx = find(diff([false; discharge_list(:)]) == 1);
endIdx = find(diff([false; discharge_list(:)]) == -1);

% Loop through each group of consecutive true values
dataPointLimit = 10;
for i = 1:length(endIdx)
    if (endIdx(i) - startIdx(i) + 1) < dataPointLimit
        % If the group has less than 10 true values, set them to false
        discharge_list(startIdx(i):endIdx(i)) = false;
    end
end

%%Store the start/end times of each of the lists w/ power as the third column
Discharge_startIdx = find(diff([false; discharge_list(:)]) == 1);
Discharge_endIdx = find(diff([false; [discharge_list(:); 0]]) == -1);
DischargeTimes = [t(Discharge_startIdx),t(Discharge_endIdx-1)];

EventPower = zeros(1,size(DischargeTimes,1));
for k =1:size(DischargeTimes,1)
    TEnvelope = find(T>=DischargeTimes(k,1) & T<=DischargeTimes(k,2));
    EventPower(k) = mean(SP(TEnvelope));
end
DischargeTimes = [DischargeTimes, EventPower'];

Sz_startIdx = find(diff([false; tenSecSz(:)]) == 1);
Sz_endIdx = find(diff([false; [tenSecSz(2:end); 0]]) == -1);
SzTimes = [t(Sz_startIdx),t(Sz_endIdx-1)];

EventPower = zeros(1,size(SzTimes,1));
for k =1:size(SzTimes,1)
    TEnvelope = find(T>=SzTimes(k,1) & T<=SzTimes(k,2));
    EventPower(k) = mean(SP(TEnvelope));
end
SzTimes = [SzTimes, EventPower'];

DischargeTrains_startIdx = find(diff([false; DischargeTrains(:)]) == 1);
DischargeTrains_endIdx = find(diff([false; [DischargeTrains(2:end); 0]]) == -1);
DischargeTrainsTimes = [t(DischargeTrains_startIdx),t(DischargeTrains_endIdx-1)];

EventPower = zeros(1,size(DischargeTrainsTimes,1));
for k =1:size(DischargeTrainsTimes,1)
    TEnvelope = find(T>=DischargeTrainsTimes(k,1) & T<=DischargeTrainsTimes(k,2));
    EventPower(k) = mean(SP(TEnvelope));
end
DischargeTrainsTimes = [DischargeTrainsTimes, EventPower'];

SE_startIdx = find(diff([false; SEList(:)]) == 1);
SE_endIdx = find(diff([false; [SEList(2:end); 0]]) == -1);
SETimes = [t(SE_startIdx),t(SE_endIdx-1)];

EventPower = zeros(1,size(SETimes,1));
for k =1:size(SETimes,1)
    TEnvelope = find(T>=SETimes(k,1) & T<=SETimes(k,2));
    EventPower(k) = mean(SP(TEnvelope));
end
SETimes = [SETimes, EventPower'];

end
