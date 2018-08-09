"""Module containing class `AdjustClipsCommand`."""


import logging
import time

from django.db import transaction

from vesper.command.command import Command
from vesper.django.app.models import AnnotationInfo, StringAnnotation
from vesper.signal.wave_audio_file import WaveAudioFileReader
import vesper.command.command_utils as command_utils
import vesper.django.app.model_utils as model_utils
import vesper.util.archive_lock as archive_lock
import vesper.util.audio_file_utils as audio_file_utils
import vesper.util.text_utils as text_utils


_logger = logging.getLogger()


class AdjustClipsCommand(Command):
    
    
    extension_name = 'adjust_clips'
    
    
    def __init__(self, args):
        
        super().__init__(args)
        
        get = command_utils.get_required_arg
        self._detector_names = get('detectors', args)
        self._sm_pair_ui_names = get('station_mics', args)
        self._classification = get('classification', args)
        self._start_date = get('start_date', args)
        self._end_date = get('end_date', args)
        self._duration = get('duration', args)
        self._center_index_annotation_name = get('annotation_name', args)
        
        self._center_index_annotation_info = \
            self._get_center_index_annotation_info()
        
        
    def _get_center_index_annotation_info(self):
        
        if len(self._center_index_annotation_name) == 0:
            return None
        
        else:
            
            try:
                return AnnotationInfo.objects.get(
                    name=self._center_index_annotation_name)
            
            except Exception:
                return None


    def execute(self, job_info):
        
        self._job_info = job_info

        self._query_annotation_name, self._query_annotation_value = \
            model_utils.get_clip_query_annotation_data(
                'Classification', self._classification)

        self._adjust_clips()
        
        return True
    
    
    def _adjust_clips(self):
        
        start_time = time.time()
        
        value_tuples = self._create_clip_query_values_iterator()
        
        total_adjusted_count = 0
        total_count = 0
        
        for detector, station, mic_output, date in value_tuples:
            
            clips = model_utils.get_clips(
                station, mic_output, detector, date,
                self._query_annotation_name, self._query_annotation_value,
                order=False)
            
            adjusted_count = 0
            count = 0
            
            for clip in clips:
                
                if self._adjust_clip(clip):
                    adjusted_count += 1
                    total_adjusted_count += 1
                    
                count += 1
                total_count += 1
                
            # Log clip count for this detector/station/mic_output/date.
            count_text = text_utils.create_count_text(count, 'clip')
            _logger.info((
                'Adjusted {} of {} for detector "{}", station "{}", mic '
                'output "{}", and date {}.').format(
                    adjusted_count, count_text, detector.name, station.name,
                    mic_output.name, date))

        # Log total clips and processing rate.
        count_text = text_utils.create_count_text(total_count, 'clip')
        elapsed_time = time.time() - start_time
        timing_text = command_utils.get_timing_text(
            elapsed_time, total_count, 'clips')
        _logger.info('Adjusted {} of a total of {}{}.'.format(
            total_adjusted_count, count_text, timing_text))


    def _create_clip_query_values_iterator(self):
        
        try:
            return model_utils.create_clip_query_values_iterator(
                self._detector_names, self._sm_pair_ui_names,
                self._start_date, self._end_date)
            
        except Exception as e:
            command_utils.log_and_reraise_fatal_exception(
                e, 'Clip query values iterator construction',
                'The archive was not modified.')

    
    def _adjust_clip(self, clip):
    
        try:
            with archive_lock.atomic():
                with transaction.atomic():
                    return self._adjust_clip_aux(clip)
                    
        except Exception as e:
            command_utils.log_and_reraise_fatal_exception(
                e, 'Processing of clip "{}"'.format(str(clip)),
                'The clip was not modified.')


    def _adjust_clip_aux(self, clip):
        
        f = model_utils.get_clip_recording_file(clip)
            
        if f is not None:
            
            # Get new clip start index and length.
            center_index = self._get_new_clip_center_index(clip)
            length = self._get_new_clip_length(clip)
            start_index = center_index - length // 2
            end_index = start_index + length
            
            if f.start_index <= start_index and end_index <= f.end_index:
                
                if start_index != clip.start_index or length != clip.length:
                    # clip bounds will change
                    
                    # _logger.info(
                    #     '({}, {}) -> ({}, {})'.format(
                    #         clip.start_index, clip.length, start_index,
                    #         length))
                    
                    # Update clip model.
                    clip.start_index = start_index
                    clip.length = length
                    clip.save()
                    
                    self._update_clip_audio_file(clip, f)
                    
                    return True
                
            else:
                
                _logger.warning(
                    ('New clip ({}, {}) would not be entirely in parent '
                     'recording file "{}". Clip will not be adjusted.').format(
                        start_index, length, str(f)))
                
                return False
                
        else:
            # recording does not have files
            
            recording = clip.recording_channel.recording
            _logger.warning(
                ('Clip recording "{}" has no files, so clip will not be '
                 'adjusted.').format(str(recording)))
            
            return False


    def _get_new_clip_center_index(self, clip):
        
        clip_center_index = clip.start_index + clip.length // 2
        
        if self._center_index_annotation_info is None:
            # archive does not include center index annotation
            
            return clip_center_index
        
        else:
            
            try:
                annotation = StringAnnotation.objects.get(
                    clip=clip, info=self._center_index_annotation_info)
                
            except Exception:
                # clip does not have center index annotation
                
                return clip_center_index
            
            else:
                # clip has center index annotation
                
                return int(annotation.value)
            

    def _get_new_clip_length(self, clip):
        
        if self._duration is None:
            return clip.length
        
        else:
            return int(round(self._duration * clip.sample_rate))
        

    def _update_clip_audio_file(self, clip, recording_file):
        
        # TODO: Create object that gets recording channel samples centered
        # around clips and use it here to get clip samples.
        
        # Get new clip samples from recording file.
        path = model_utils.get_absolute_recording_file_path(recording_file)
        reader = WaveAudioFileReader(str(path))
        start_index = clip.start_index - recording_file.start_index
        samples = reader.read(start_index, clip.length)
        samples = samples[clip.recording_channel.channel_num]
        samples.shape = (1, len(samples))
        
        # Write new clip audio file.
        path = clip.wav_file_path
        audio_file_utils.write_wave_file(path, samples, clip.sample_rate)
