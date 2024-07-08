function save_channel_to_mat(channel_data, temp_data_path)
  % Create the MAT file name with the temp_data_path
  mat_filename = fullfile(temp_data_path, sprintf('temp_data_%d_%d.mat', channel_data.name));

  % Write the data to the MAT file (with multiple attempts)
  max_attempts = 3;
  for attempt = 1:max_attempts
    try
      signal = channel_data.signal;
      name = channel_data.name;
      SzTimes = channel_data.SzTimes;
      SETimes = channel_data.SETimes;
      DischargeTimes = channel_data.DischargeTimes;
      DischargeTrainsTimes = channel_data.DischargeTrainsTimes;

      save(mat_filename, 'signal', 'name', 'SzTimes', 'SETimes', 'DischargeTimes', 'DischargeTrainsTimes');
      break;  % Exit the loop if the file is saved successfully
    catch
      if attempt == max_attempts
        error('Failed to save the MAT file "%s" after %d attempts.', mat_filename, max_attempts);
      else
        pause(1);  % Wait for a short interval before the next attempt
      end
    end
  end
end
