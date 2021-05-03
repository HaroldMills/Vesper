"""Module containing class `CreateClipAudioFilesCommand`."""


import logging
import time

from vesper.command.clip_set_command import ClipSetCommand
from vesper.singleton.clip_manager import clip_manager
import vesper.command.command_utils as command_utils
import vesper.django.app.model_utils as model_utils
import vesper.util.text_utils as text_utils


_logger = logging.getLogger()


class CreateClipAudioFilesCommand(ClipSetCommand):
    
    
    extension_name = 'create_clip_audio_files'
    
    
    def __init__(self, args):
        super().__init__(args, True)
        
        
    def execute(self, job_info):
        self._job_info = job_info
        self._create_clip_audio_files()
        return True
    
    
    def _create_clip_audio_files(self):
        
        start_time = time.time()
        
        value_tuples = self._create_clip_query_values_iterator()
        
        total_num_clips = 0
        total_num_created_files = 0
        
        for station, mic_output, date, detector in value_tuples:
            
            clips = model_utils.get_clips(
                station=station,
                mic_output=mic_output,
                date=date,
                detector=detector,
                annotation_name=self._annotation_name,
                annotation_value=self._annotation_value,
                tag_name=self._tag_name,
                order=False)
            
            num_clips = len(clips)
            num_created_files = 0
            
            for clip in clips:
                if self._create_clip_audio_file_if_needed(clip):
                    num_created_files += 1
                
            # Log file creations for this detector/station/mic_output/date.
            count_text = text_utils.create_count_text(num_clips, 'clip')
            _logger.info(
                f'Created audio files for {num_created_files} of '
                f'{count_text} for station "{station.name}", '
                f'mic output "{mic_output.name}", date {date}, '
                f'and detector "{detector.name}".')
                
            total_num_clips += num_clips
            total_num_created_files += num_created_files
            
        # Log total file creations and creation rate.
        count_text = text_utils.create_count_text(total_num_clips, 'clip')
        elapsed_time = time.time() - start_time
        timing_text = command_utils.get_timing_text(
            elapsed_time, total_num_clips, 'clips')
        _logger.info(f'Processed a total of {count_text}{timing_text}.')


    def _create_clip_audio_file_if_needed(self, clip):
        
        try:
            
            if not clip_manager.has_audio_file(clip):
                clip_manager.create_audio_file(clip)
                return True
            
            else:
                return False
                    
        except Exception as e:
            command_utils.log_and_reraise_fatal_exception(
                e, f'Creation of audio file for clip "{str(clip)}"')
