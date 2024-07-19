function [SzTimes,DischargeTimes,SETimes] = SzSEDetectLEGIT(V,sampRate,t,do_analysis)
if ~do_analysis
    DischargeTimes = [];
    SzTimes = [];
    SETimes = [];
    return
end
if height(V) ~= 1
  V = V';
end
%Timing Variables
ScanSize = 2; %sec
Vthresh = 6; %STD
varThresh = 6; %STD
LookAheadTime = 10; %sec
SELimTime = 25; %sec
SEDurLim = ceil(5*60*sampRate); %min*60s/min
RefInc = 1.2;

% Determine Reference section
Refsize = 2; %min
% Specify the step size for the window
step_size = floor(sampRate); %.5sec

TotRefCheck = floor(t(end) / 4); %Check whole rec

% Set the window size
window_size = ceil(sampRate*60*Refsize);
VtoCheck = floor(sampRate*60*TotRefCheck);



% Initialize
range = ceil(sampRate*15):step_size:(VtoCheck - window_size + 1); %exclude 1st minute
refSeek = true;
coef = .5;

% Find the first valid ref section without peaks
warning('off', 'signal:findpeaks:largeMinPeakHeight');
while refSeek
    refpeakThresh = mean(abs(V))+ coef*std(abs(V)); 
    for i = 1:numel(range)
        end_index = range(i) + window_size - 1;
    
        % Check if the end index exceeds the size of V
        if end_index > numel(V)
            break;  % Exit the loop if the index is out of bounds
        end
    
        window_data = V(range(i):end_index);
        [~, locs] = findpeaks(abs(window_data),"MinPeakHeight",refpeakThresh);
        if isempty(locs) %Exit and store when a valid reference is found
            refRange = range(i):1:end_index;
            refSeek = false; 
            break
        end
    end
    coef = coef*RefInc; %increase threshold by 20% for peak disqualification if no ref sections found
    RefInc = RefInc^2;
end
warning('on', 'signal:findpeaks:largeMinPeakHeight');    
%Store the reference sections as unique lists
tRef = [t(refRange(1)),t(refRange(end))];
VRef = V(refRange);

%Determine the areas that are significantly different given the reference section
ref_mean = mean(abs(VRef));
ref_std = std(abs(VRef));
Vuplim = ref_mean + Vthresh*ref_std;
outlier_indices = find(abs(V) > Vuplim);

window_size = ScanSize * ceil(sampRate);
half_window = floor(window_size / 2);

% Calculate moving variance
moving_var = movvar(V, window_size, 'Endpoints', 'discard');

% Create centered tVar
tVar = t(half_window:(end - half_window));

% % If needing to go by more than a step size of one
% Var_step_size = 1; %data point 
% moving_var = moving_var(1:Var_step_size:end);
% tVar = tVar(1:Var_step_size:end);

refVar = moving_var((find(tVar>=tRef(1),1)):(find(tVar>=tRef(2),1)));
varLim = mean(refVar) + varThresh*std(refVar);

%First check (discharge list)
PassPts = false(size(t)); %initialize list
chkpts = outlier_indices(outlier_indices>((sampRate*ScanSize)/2)); %remove pts in first second (need 1sec before and after)

% Vectorized approach
adjust = find(t == tVar(1))-1; %adjust for the window size of the variance
moving_varMod = [ zeros(1,adjust), moving_var,zeros(1,adjust+1)];

moving_var_values = moving_varMod(chkpts);
PassPts(chkpts) = moving_var_values > varLim;

%Process to group together clusters of identified discharges
checkLim = ceil(ScanSize*sampRate);
discharge_list = false(size(PassPts));

% Find indices of true values
trueIndices = find(PassPts);

% Calculate differences between consecutive true indices
diffIndices = diff(trueIndices);

% Find pairs of true values within checkLim
withinLimit = diffIndices <= checkLim;

% Create a matrix where each row represents a range to be marked
ranges = [trueIndices(withinLimit), trueIndices(find(withinLimit) + 1)];

% Use logical indexing to mark all points within these ranges
for i = 1:size(ranges, 1)
    discharge_list(ranges(i,1):ranges(i,2)) = true;
end

%Parse out the 10sec Szs
LenLim = sampRate*10;

% Initialize the new logical list with false values
tenSecSz = false(size(discharge_list));

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

SzEndIdxs = find(diff([false; tenSecSz(:)]) == -1);

%After a Sz, check for discharges after 
EventLim = ceil(LookAheadTime*sampRate);
% Create a new logical array the same size as discharge_list, initialized to false
AfterDischarges = false(size(discharge_list));

for idx = SzEndIdxs'
    current_idx = idx;
    while current_idx <= length(discharge_list)
        % Define the range to check
        end_idx = min(current_idx + EventLim - 1, length(discharge_list));
        
        % Check if there are any true values in the range
        if any(discharge_list(current_idx:end_idx))
            %find last true in range:
            trueInRange = find(discharge_list(current_idx:end_idx));
            nextTrue = current_idx +trueInRange(end);
            % Mark all intervening points as true

            AfterDischarges(current_idx-1:nextTrue) = true;
            % Move to the next section
            current_idx = nextTrue + 1;
        else
            % No true values found, stop looking for this index
            break;
        end
    end
end

%Parse out the SE
SELim = sampRate*SELimTime; %How close together discharges must be
SECand = false(size(discharge_list));

% Find indices of true values
SEtrueIndices = find(PassPts);

%iterate through the points
for SEpt = 1:(length(SEtrueIndices')-1)
    toNextPt = SEtrueIndices(SEpt+1) - SEtrueIndices(SEpt);
    if toNextPt <= SELim
        SECand(SEtrueIndices(SEpt):SEtrueIndices(SEpt+1)) = true;
    end
end

SEList = false(size(discharge_list));

% Find the start and end indices of each sequence of true values
SECstarts = find(diff([false; SECand(:)]) == 1);
SECends = find(diff([SECand(:); false]) == -1);

% Loop through each sequence and check its length
for i = 1:length(SECstarts)
    if (SECends(i) - SECstarts(i) + 1) >= SEDurLim
        % Preserve the true values for sequences that are at least SEDurLim long
        SEList(SECstarts(i):SECends(i)) = true;
    end
end

%Add afterdischarges to Sz
tenSecSz = tenSecSz | AfterDischarges;

%Remove Szs in SE
tenSecSz(tenSecSz & SEList) = false;

%Remove categorized discharges
discharge_list(discharge_list & tenSecSz) = false;
discharge_list(discharge_list & SEList) = false;

Sz_startIdx = find(diff([false; tenSecSz(:)]) == 1);
Sz_endIdx = find(diff([false; [tenSecSz(2:end); 0]]) == -1);
SzTimes = [t(Sz_startIdx),t(Sz_endIdx-1)]; %#ok
EventPower = zeros(1,size(SzTimes,1));
for k =1:size(SzTimes,1)
    TEnvelope = find(t>=SzTimes(k,1) & t<=SzTimes(k,2));
    EventPower(k) = mean(moving_varMod(TEnvelope)); %#ok
end
SzTimes = [SzTimes, EventPower'];

D_startIdx = find(diff([false; discharge_list(:)]) == 1);
D_endIdx = find(diff([false; [discharge_list(2:end); 0]]) == -1);
DTimes = [t(D_startIdx),t(D_endIdx-1)]; %#ok
EventPower = zeros(1,size(DTimes,1));
for k =1:size(DTimes,1)
    TEnvelope = find(t>=DTimes(k,1) & t<=DTimes(k,2));
    EventPower(k) = mean(moving_varMod(TEnvelope)); %#ok
end 
DischargeTimes = [DTimes, EventPower'];

SE_startIdx = find(diff([false; SEList(:)]) == 1);
SE_endIdx = find(diff([false; [SEList(2:end); 0]]) == -1);
SETimes = [t(SE_startIdx),t(SE_endIdx-1)]; %#ok
EventPower = zeros(1,size(SETimes,1));
for k =1:size(SETimes,1)
    TEnvelope = find(t>=SETimes(k,1) & t<=SETimes(k,2));
    EventPower(k) = mean(moving_varMod(TEnvelope)); %#ok
end
SETimes = [SETimes, EventPower'];

end
