function [total_channels, sampRate, NRecFrames] = get_cat_envelop_parallel(FileName, temp_data_path, do_analysis)
    FilePath = FileName;
    
    disp('=== Starting get_cat_envelop_parallel ===');
    disp(['Processing file: ', FilePath]);
    disp(['Temporary data path: ', temp_data_path]);
    
    % Check if temp_data_path exists
    if ~exist(temp_data_path, 'dir')
        error('Temporary data directory does not exist: %s', temp_data_path);
    end
    
    % Read file information
    disp('Reading file information...');
    recElectrodeList = h5read(FilePath, '/3BRecInfo/3BMeaStreams/Raw/Chs');
    NRecFrames = double(h5read(FilePath, '/3BRecInfo/3BRecVars/NRecFrames'));
    sampRate = h5read(FilePath, '/3BRecInfo/3BRecVars/SamplingRate');
    signalInversion = h5read(FilePath, '/3BRecInfo/3BRecVars/SignalInversion');
    maxUVolt = double(h5read(FilePath, '/3BRecInfo/3BRecVars/MaxVolt'));
    minUVolt = double(h5read(FilePath, '/3BRecInfo/3BRecVars/MinVolt'));
    bitDepth = h5read(FilePath, '/3BRecInfo/3BRecVars/BitDepth');
    
    % Display file information
    disp(['NRecFrames: ', num2str(NRecFrames)]);
    disp(['sampRate: ', num2str(sampRate)]);
    disp(['signalInversion: ', num2str(signalInversion)]);
    disp(['maxUVolt: ', num2str(maxUVolt)]);
    disp(['minUVolt: ', num2str(minUVolt)]);
    disp(['bitDepth: ', num2str(bitDepth)]);

    % Calculate conversion factors
    qLevel = double(bitxor(2, bitDepth));
    fromQLevelToUVolt = (maxUVolt - minUVolt) / qLevel;
    ADCCountsToMV = double(signalInversion) * fromQLevelToUVolt;
    MVOffset = double(signalInversion) * minUVolt;

    % Get channel information
    [Rows, Cols] = getChs(FileName);
    total_channels = length(Rows);
    
    disp(['Total channels: ', num2str(total_channels)]);

    % Get dataset info
    info = h5info(FilePath, '/3BData/Raw');
    datasetSize = info.Dataspace.Size;
    
    % Calculate the number of samples per channel
    samples_per_channel = datasetSize(1) / total_channels;
    disp(['Samples per channel: ', num2str(samples_per_channel)]);

    % Define chunk size (adjust as needed)
    chunk_size = min(100000, samples_per_channel);
    total_chunks = ceil(samples_per_channel / chunk_size);
    disp(['Total number of chunks to process: ', num2str(total_chunks)]);

    % Process data in chunks
    for chunk_index = 1:total_chunks
        chunk_start = (chunk_index - 1) * chunk_size + 1;
        chunk_end = min(chunk_start + chunk_size - 1, samples_per_channel);
        chunk_length = chunk_end - chunk_start + 1;

        disp(['Processing chunk ', num2str(chunk_index), ' of ', num2str(total_chunks)]);

        % Prepare start and count parameters for h5read
        start = double((chunk_start - 1) * total_channels + 1);
        count = double(chunk_length * total_channels);

        % Read chunk of data
        chunk_data = h5read(FilePath, '/3BData/Raw', start, count);
        chunk_data = double(chunk_data);  % Ensure data is in double format
        chunk_data = reshape(chunk_data, total_channels, []);

        % Process each channel in parallel
        parfor k = 1:total_channels
            try
                process_channel(k, chunk_data, chunk_start, chunk_end, Rows, Cols, ...
                                NRecFrames, ADCCountsToMV, MVOffset, sampRate, ...
                                do_analysis, temp_data_path, chunk_index == total_chunks);
            catch ME
                warning('Error processing channel %d: %s\nStack trace: %s', k, ME.message, getReport(ME));
            end
        end
    end

    disp('=== Processing complete ===');
end

function process_channel(k, chunk_data, chunk_start, chunk_end, Rows, Cols, ...
                         NRecFrames, ADCCountsToMV, MVOffset, sampRate, ...
                         do_analysis, temp_data_path, is_last_chunk)
    tgt_rows = Rows(k);
    tgt_cols = Cols(k);

    % Extract and process channel data
    channel_data = chunk_data(k, :)';
    channel_data = double(channel_data);  % Ensure data is in double format
    channel_data = (channel_data * ADCCountsToMV) + MVOffset;
    channel_data = channel_data / 1000000;  % Convert to volts

    % Load existing data or create new
    filename = fullfile(temp_data_path, sprintf('temp_data_%d_%d.mat', tgt_rows, tgt_cols));
    if exist(filename, 'file')
        load(filename, 'signal');
    else
        signal = zeros(NRecFrames, 1);
    end

    % Update the signal
    signal(chunk_start:chunk_end) = channel_data;

    % Prepare channel_data structure
    channel_struct = struct('signal', signal, 'name', [tgt_rows, tgt_cols], ...
                            'SzTimes', [], 'SETimes', [], ...
                            'DischargeTimes', [], 'DischargeTrainsTimes', []);

    % Save updated signal
    save_channel_to_mat(channel_struct, temp_data_path);

    % If it's the last chunk, perform analysis and save results
    if is_last_chunk
        signal = signal - mean(signal);  % Remove DC offset

        % Perform seizure detection
        [DischargeTimes, SzTimes, DischargeTrainsTimes, SETimes] = SzDetectCat(signal, sampRate, do_analysis);

        % Update channel_struct with analysis results
        channel_struct.SzTimes = SzTimes;
        channel_struct.SETimes = SETimes;
        channel_struct.DischargeTimes = DischargeTimes;
        channel_struct.DischargeTrainsTimes = DischargeTrainsTimes;

        % Save the analysis results
        save_channel_to_mat(channel_struct, temp_data_path);
    end
end
