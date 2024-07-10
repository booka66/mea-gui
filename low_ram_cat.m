function [total_channels, sampRate, NRecFrames] = get_cat_envelop(FileName, temp_data_path, do_analysis)
    FilePath = FileName;
    
    disp('Reading file information...');
    recElectrodeList = h5read(FilePath, '/3BRecInfo/3BMeaStreams/Raw/Chs');
    NRecFrames = double(h5read(FilePath, '/3BRecInfo/3BRecVars/NRecFrames'));
    sampRate = h5read(FilePath, '/3BRecInfo/3BRecVars/SamplingRate');
    signalInversion = h5read(FilePath, '/3BRecInfo/3BRecVars/SignalInversion');
    maxUVolt = double(h5read(FilePath, '/3BRecInfo/3BRecVars/MaxVolt'));
    minUVolt = double(h5read(FilePath, '/3BRecInfo/3BRecVars/MinVolt'));
    bitDepth = h5read(FilePath, '/3BRecInfo/3BRecVars/BitDepth');
    
    disp(['NRecFrames: ', num2str(NRecFrames)]);
    disp(['sampRate: ', num2str(sampRate)]);
    disp(['signalInversion: ', num2str(signalInversion)]);
    disp(['maxUVolt: ', num2str(maxUVolt)]);
    disp(['minUVolt: ', num2str(minUVolt)]);
    disp(['bitDepth: ', num2str(bitDepth)]);

    qLevel = double(bitxor(2, bitDepth));
    fromQLevelToUVolt = (maxUVolt - minUVolt) / qLevel;
    ADCCountsToMV = signalInversion * fromQLevelToUVolt;
    MVOffset = signalInversion * minUVolt;

    disp(['qLevel: ', num2str(qLevel)]);
    disp(['fromQLevelToUVolt: ', num2str(fromQLevelToUVolt)]);
    disp(['ADCCountsToMV: ', num2str(ADCCountsToMV)]);
    disp(['MVOffset: ', num2str(MVOffset)]);

    rows = recElectrodeList.Row;
    cols = recElectrodeList.Col;
    channels = horzcat(cols, rows);
    total_channels = length(channels(:,1));
    
    disp(['Total channels: ', num2str(total_channels)]);

    [Rows, Cols] = getChs(FileName);
    disp(['Rows size: ', mat2str(size(Rows))]);
    disp(['Cols size: ', mat2str(size(Cols))]);

    % Initialize data structure
    disp('Initializing data structure...');
    data = struct();
    for x = 1:64
        for y = 1:64
            data(x, y).signal = zeros(NRecFrames, 1);
            data(x, y).name = [x y];
            data(x, y).SzTimes = [];
            data(x, y).SETimes = [];
            data(x, y).DischargeTimes = [];
            data(x, y).DischargeTrainsTimes = [];
        end
    end
    disp('Data structure initialized.');

    % Get dataset info
    disp('Getting dataset info...');
    info = h5info(FilePath, '/3BData/Raw');
    datasetSize = info.Dataspace.Size;
    disp(['Dataset size: ', mat2str(datasetSize)]);
    disp(['Dataset rank: ', num2str(length(datasetSize))]);

    % Calculate the number of samples per channel
    samples_per_channel = datasetSize(1) / total_channels;
    disp(['Samples per channel: ', num2str(samples_per_channel)]);

    % Define chunk size (adjust as needed)
    chunk_size = min(1000000, samples_per_channel);  % Number of samples to read at once
    disp(['Chunk size: ', num2str(chunk_size)]);

    % Process data in chunks
    for chunk_start = 1:chunk_size:samples_per_channel
        chunk_end = min(chunk_start + chunk_size - 1, samples_per_channel);
        chunk_length = chunk_end - chunk_start + 1;

        disp(['Processing chunk: ', num2str(chunk_start), ' to ', num2str(chunk_end)]);

        % Prepare start and count parameters
        start = double((chunk_start - 1) * total_channels + 1);
        count = double(chunk_length * total_channels);

        disp(['Start: ', mat2str(start)]);
        disp(['Count: ', mat2str(count)]);

        % Read chunk of data
        try
            chunk_data = h5read(FilePath, '/3BData/Raw', start, count);
            disp(['Chunk data size: ', mat2str(size(chunk_data))]);
        catch ME
            disp('Error reading chunk:');
            disp(getReport(ME));
            rethrow(ME);
        end

        chunk_data = double(chunk_data);

        % Reshape chunk data to separate channels
        chunk_data = reshape(chunk_data, total_channels, []);

        % Process each channel
        for k = 1:total_channels
            chNum = k;
            tgt_cols = Cols(chNum);
            tgt_rows = Rows(chNum);

            disp(['Processing channel: ', num2str(k), ' (Row: ', num2str(tgt_rows), ', Col: ', num2str(tgt_cols), ')']);

            % Extract and process channel data
            channel_data = chunk_data(k, :)';
            
            disp(['Channel data size: ', mat2str(size(channel_data))]);

            channel_data = (channel_data * ADCCountsToMV) + MVOffset;
            channel_data = channel_data / 1000000;

            % Update the signal in the data structure
            data(tgt_rows, tgt_cols).signal(chunk_start:chunk_end) = channel_data;

            % If it's the last chunk, perform analysis
            if chunk_end == samples_per_channel
                disp(['Performing analysis for channel: ', num2str(k)]);
                signal = data(tgt_rows, tgt_cols).signal;
                signal = signal - mean(signal);

                disp('Calling SzDetectCat...');
                [DischargeTimes, SzTimes, DischargeTrainsTimes, SETimes] = SzDetectCat(signal, sampRate, do_analysis);
                disp('SzDetectCat completed.');

                % Update the data structure with results
                data(tgt_rows, tgt_cols).name = [tgt_rows tgt_cols];
                data(tgt_rows, tgt_cols).SzTimes = SzTimes;
                data(tgt_rows, tgt_cols).SETimes = SETimes;
                data(tgt_rows, tgt_cols).DischargeTimes = DischargeTimes;
                data(tgt_rows, tgt_cols).DischargeTrainsTimes = DischargeTrainsTimes;

                % Save the channel data to a MAT file
                disp(['Saving channel data to MAT file for channel: ', num2str(k)]);
                save_channel_to_mat(data(tgt_rows, tgt_cols), temp_data_path);
                disp('Channel data saved.');
            end
        end
    end

    disp('Processing complete.');
end
