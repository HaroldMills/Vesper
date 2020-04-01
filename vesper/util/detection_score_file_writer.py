"""Module containing `DetectionScoreFileWriter` class."""


import wave

import numpy as np

import vesper.util.signal_utils as signal_utils


class DetectionScoreFileWriter:
    
    """
    Writes a wave file containing detector audio input in one channel
    and detection scores in another.
    """
    
    
    def __init__(
            self, file_path, sample_rate, score_scale_factor,
            score_repetition_factor, output_start_offset=0,
            output_duration=None):
        
        self._sample_rate = sample_rate
        self._score_scale_factor = score_scale_factor
        self._score_repetition_factor = score_repetition_factor

        self._output_start_index = signal_utils.seconds_to_frames(
            output_start_offset, sample_rate)
        
        if output_duration is None:
            self._output_end_index = None
        else:
            max_file_length = signal_utils.seconds_to_frames(
                output_duration, sample_rate)
            self._output_end_index = self._output_start_index + max_file_length
        
        # Open wave file.
        self._writer = wave.open(file_path, 'wb')
        self._writer.setparams((2, 2, sample_rate, 0, 'NONE', None))
        
        self._samples_start_index = 0

        
    def write(self, samples, scores):
         
        num_samples = len(samples)
       
        initial_skip_size = min(
            max(self._output_start_index - self._samples_start_index, 0),
            num_samples)

        if self._output_end_index is None:
            final_skip_size = 0
        else:
            end_index = self._samples_start_index + num_samples
            final_skip_size = min(
                max(end_index - self._output_end_index, 0),
                num_samples)
       
        write_size = num_samples - (initial_skip_size + final_skip_size)
       
        if write_size != 0:
       
            # Convert samples to wave file data type.
            samples = np.array(np.round(samples), dtype='<i2')
           
            # Scale scores and convert to wave file data type.
            scores = scores * self._score_scale_factor
            scores = np.array(np.round(scores), dtype='<i2')
           
            # Repeat each score `self._score_repetition_factor` times.
            scores = scores.reshape((len(scores), 1))
            ones = np.ones((1, self._score_repetition_factor), dtype='<i2')
            scores = (scores * ones).flatten()
           
            # Append zeros to scores if needed to make length equal to
            # that of samples.
            if len(scores) < num_samples:
                zeros = np.zeros(num_samples - len(scores), dtype='<i2')
                scores = np.concatenate((scores, zeros))
           
            # Slice samples and scores.
            start_index = initial_skip_size
            end_index = start_index + write_size
            samples = samples[start_index:end_index]
            scores = scores[start_index:end_index]
           
            # Stack samples and scores to make two "audio" channels.
            samples = np.vstack((samples, scores))
           
            # Interleave channel samples and convert to bytes.
            data = samples.transpose().tobytes()
           
            self._writer.writeframes(data)
           
        self._samples_start_index += num_samples
        
        
    def close(self):
        self._writer.close()
