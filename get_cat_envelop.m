function [total_channels,sampRate,NRecFrames] = get_cat_envelop(FileName, temp_data_path, do_analysis)
FilePath = FileName;
recElectrodeList = h5read(FilePath, '/3BRecInfo/3BMeaStreams/Raw/Chs');
NRecFrames = h5read(FilePath, '/3BRecInfo/3BRecVars/NRecFrames');
NRecFrames = double(NRecFrames);
sampRate = h5read(FilePath, '/3BRecInfo/3BRecVars/SamplingRate');
signalInversion = h5read(FilePath, '/3BRecInfo/3BRecVars/SignalInversion');
maxUVolt = h5read(FilePath, '/3BRecInfo/3BRecVars/MaxVolt');
maxUVolt = double(maxUVolt);
minUVolt = h5read(FilePath, '/3BRecInfo/3BRecVars/MinVolt');
minUVolt = double(minUVolt);
bitDepth = h5read(FilePath, '/3BRecInfo/3BRecVars/BitDepth');
qLevel = bitxor(2,bitDepth);
qLevel = double(qLevel);
fromQLevelToUVolt = (maxUVolt - minUVolt) / qLevel;
ADCCountsToMV = signalInversion * fromQLevelToUVolt;
ADCCountsToMV = double(ADCCountsToMV);
MVOffset = signalInversion * minUVolt;
rows = recElectrodeList.Row;
cols = recElectrodeList.Col;
channels = horzcat(cols, rows);
total_channels = length(channels(:,1));
full_data = h5read(FilePath, '/3BData/Raw');
full_data = double(full_data);
reshaped_full_data = zeros(NRecFrames, total_channels);
for i = 1:total_channels
    reshaped_full_data(:, i) = full_data(i:total_channels:end);
end
full_data = reshaped_full_data;
[Rows, Cols] = getChs(FileName);
data = struct();
for x = 1:64
    for y = 1:64
        data(x, y).signal = zeros(NRecFrames, 1);
        data(x, y).name = [x y];
        data(x, y).SzTimes = [];
        data(x, y).SETimes = [];
        data(x, y).DischargeTimes = [];
    end
end
temp_data = cell(total_channels, 1);
t = transpose(linspace(1 / sampRate, NRecFrames / sampRate, NRecFrames));
parfor k = 1:total_channels
    chNum = k;
    tgt_cols = [Cols(chNum)];
    tgt_rows = [Rows(chNum)];
    tgt_indexes = zeros(1, length(tgt_rows));
    
    for i = 1:length(tgt_rows)
        [rowIndex, ~] = find((channels(:,1) == tgt_cols(i)) & (channels(:,2) == tgt_rows(i)));
        tgt_indexes(i) = rowIndex;
    end
    
    channel_data = zeros(NRecFrames, length(tgt_indexes));
    
    channel_data = full_data(:, tgt_indexes);
    channel_data = (channel_data * ADCCountsToMV) + double(MVOffset);
    channel_data = channel_data / 1000000;
    channel_data = channel_data - mean(channel_data, 1);
    
    signal = channel_data(:, 1);

    
    % Red, Green, Blue, Yellow
    [SzTimes, DischargeTimes, SETimes] = SzSEDetectLEGIT(signal, sampRate, t, do_analysis);
    
    temp_data{k} = struct('signal', signal, ...
                          'name', [tgt_rows tgt_cols], ...
                          'SzTimes', SzTimes, ...
                          'SETimes', SETimes, ...
                          'DischargeTimes', DischargeTimes);
    % Save the channel data to a MAT file in the specified temp_data directory (with multiple attempts)
    save_channel_to_mat(temp_data{k}, temp_data_path);
end
