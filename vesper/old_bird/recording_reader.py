import wave

import numpy as np


class RecordingReader:
    
    
    def __init__(self, files):
        self._file_readers = self._get_file_readers(files)
        
        
    def _get_file_readers(self, files):
        
        if len(files) == 0:
            raise Exception(
                'Archive database contains no files for recording.')
            
        return [_RecordingFileReader(f) for f in files]
    
    
    def read_samples(self, channel_num, start_index, length):
        
        num_files = len(self._file_readers)
        
        file_num, read_index = self._get_read_start_data(start_index)
        
        samples = np.empty(length, dtype='int16')
        write_index = 0
        
        remaining = length

        while file_num != num_files and remaining != 0:
            
            reader = self._file_readers[file_num]
            read_length = min(reader.file.length - read_index, remaining)
            
            reader.read_samples(
                channel_num, read_index, read_length, samples, write_index)
            
            file_num += 1
            read_index = 0
            write_index += read_length
            remaining -= read_length
            
        return samples
            
            
    def _get_read_start_data(self, start_index):
        
        for file_num, reader in enumerate(self._file_readers):
            
            file_start_index = reader.file.start_index
            file_end_index = reader.file.start_index + reader.file.length
            
            if start_index >= file_start_index and \
                    start_index < file_end_index:
                    # read starts in this file
                    
                read_index = start_index - file_start_index
                return file_num, read_index
            
        # If we get here, start index is past end of last file.
        raise Exception(
            f'Read start index {start_index} is past end of recording '
            f'of length {file_end_index}.')
                
                
class _RecordingFileReader:
    
    
    def __init__(self, file_):
        
        # `file_` needs the following members:
        #
        #    path: absolute path of audio file
        #    start_index: start index in recording of audio file
        #    length: length of audio file in sample frames
        
        self._file = file_
        
        
    @property
    def file(self):
        return self._file
    
    
    def read_samples(
            self, channel_num, read_index, num_frames, samples, write_index):
        
        try:
            reader = wave.open(str(self._file.path), 'rb')
        except Exception as e:
            self._handle_file_error('Open failed', e)
        
        with reader:
            
            try:
                reader.setpos(read_index)
            except Exception as e:
                self._handle_file_error('Set of read position failed', e)
                
            try:
                buffer = reader.readframes(num_frames)
            except Exception as e:
                self._handle_file_error('Samples read failed', e)
 
            s = np.frombuffer(buffer, dtype='<i2')
            s = s.reshape((num_frames, reader.getnchannels()))
            s = s.transpose()
            
            samples[write_index:write_index + num_frames] = s[channel_num]
        
        
    def _handle_file_error(self, prefix, exception):
        raise Exception(
            f'{prefix} for audio file "{self._file.path}" '
            f'with message: {str(exception)}')
