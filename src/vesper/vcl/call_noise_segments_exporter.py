"""Module containing class `CallNoiseSegmentsExporter`."""


from __future__ import print_function
import os.path
import random

import h5py

from vesper.vcl.clip_visitor import ClipVisitor
import vesper.vcl.vcl_utils as vcl_utils


class CallNoiseSegmentsExporter(ClipVisitor):


    def __init__(self, positional_args, keyword_args):
        
        super(CallNoiseSegmentsExporter, self).__init__(
            positional_args, keyword_args)
        
        self._file_path = vcl_utils.get_required_keyword_arg(
            'output-path', keyword_args)[0]
            
        self._segment_dur = float(
            vcl_utils.get_required_keyword_arg(
                'segment-duration', keyword_args)[0])
        
        self._min_segment_spacing = float(
            keyword_args.get('min-segment-spacing', ('0',))[0])
        
        
    export = ClipVisitor.visit_clips
        
        
    def begin_visits(self):
        
        # It is important to provide the random number generator with
        # the same seed each time this method runs, so that this script
        # will output the same segments for the same input each time it
        # runs.
        random.seed(0)
        
        self._clip_count = 0
        self._call_count = 0
        self._noise_count = 0
        self._short_clips = []
        
        self._file = h5py.File(self._file_path, 'w')
        
        
    def visit(self, clip):
        
        if clip.selection is None:
            return
            
        self._clip_count += 1
        
        # Split file name into components.
        file_name = os.path.basename(clip.file_path)
        (station_name, detector_name, date, time, _) = file_name.split('_')

        # Get prefix for HDF5 dataset names.
        dataset_name_prefix = '_'.join(
            (station_name, detector_name, date, time))
        
        # Format clip start time using colons rather than dots in time of day.
        h, m, s, f = time.split('.')
        time = ':'.join([h, m, s + '.' + f])
        clip_start_time = date + ' ' + time
            
        selection_start_index, selection_length = clip.selection
        sample_rate = clip.sound.sample_rate
        segment_length = _seconds_to_samples(self._segment_dur, sample_rate)
        
        if selection_length < segment_length:
            # clip selection not long enough to extract segment from
            
            self._short_clips.append(clip)
            
        else:
            # clip selection is long enough to extract segment from
            
            # Extract call samples from selection.
            offset = random.randrange(selection_length - segment_length)
            segment_start_index = selection_start_index + offset
            end_index = segment_start_index + segment_length
            samples = clip.sound.samples[segment_start_index:end_index]
            
            # Write call samples to HDF5 file.
            dataset_name = '_'.join(
                (dataset_name_prefix, str(segment_start_index)))
            self._file[dataset_name] = samples
            
            # Set call segment attributes in HDF5 file.
            attrs = self._file[dataset_name].attrs
            attrs['station_name'] = station_name
            attrs['detector_name'] = detector_name
            attrs['clip_start_time'] = clip_start_time
            attrs['sample_rate'] = sample_rate
            attrs['segment_start_index'] = segment_start_index
            attrs['classification'] = 'Call'
            
            self._call_count += 1
            
        # Get noise segment start index.
        spacing = _seconds_to_samples(self._min_segment_spacing, sample_rate)
        num_samples = selection_start_index - spacing
        if num_samples > segment_length:
            stop = num_samples - segment_length
            segment_start_index = random.randrange(stop)
        else:
            segment_start_index = None
            
        if segment_start_index is not None:
            
            # Extract noise samples from clip.
            end_index = segment_start_index + segment_length
            samples = clip.sound.samples[segment_start_index:end_index]
            
            # Write samples to HDF5 file.
            dataset_name = '_'.join(
                (dataset_name_prefix, str(segment_start_index)))
            self._file[dataset_name] = samples

            # Set call segment attributes in HDF5 file.
            attrs = self._file[dataset_name].attrs
            attrs['station_name'] = station_name
            attrs['detector_name'] = detector_name
            attrs['clip_start_time'] = clip_start_time
            attrs['sample_rate'] = sample_rate
            attrs['segment_start_index'] = segment_start_index
            attrs['classification'] = 'Noise'
            
            self._noise_count += 1
            
        
    def end_visits(self):
        self._file.close()
        print('found {:d} clips with selections'.format(self._clip_count))
        print('extracted {:d} call segments and {:d} noise segments'.format(
            self._call_count, self._noise_count))
        self._show_short_clips()
        _show_hdf5_file(self._file_path)
        
        
    def _show_short_clips(self):
        n = len(self._short_clips)
        if n != 0:
            print('found {:d} short clips:'.format(n))
            for clip in self._short_clips:
                file_name = os.path.basename(clip.file_path)
                start_index, length = clip.selection
                print('    {:s} {:d} {:d}...'.format(
                    file_name, start_index, length))


def _seconds_to_samples(duration, sample_rate):
    return int(round(duration * sample_rate))


def _show_hdf5_file(file_path):
    
    try:
        file_ = h5py.File(file_path, 'r')
        
    except IOError:
        pass
    
    else:
        
        print('segments:')
        
        for name in file_:
            s = file_[name]
            print('   ', name, s.shape)
            for name, value in s.attrs.iteritems():
                print('       ', name + ':', value)
        
        file_.close()
