function [rows,cols] = getChs(FilePath)
%READ_AND_CLEAN takes an hdf5 brainwave file and cleans it
%   INPUTS: file_path, array of target columns, array of target rows
%   OUTPUTS: array of channel data, sampRate, NRecFrames
    recElectrodeList = h5read(FilePath, '/3BRecInfo/3BMeaStreams/Raw/Chs');
    rows = recElectrodeList.Row;
    cols = recElectrodeList.Col;  
end