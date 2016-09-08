"""
Module containing function that runs a detector on a file channel.

A Vesper `detect` command runs the `run_detector` function in a separate
process for each combination of a detector and a recording file channel
on which the detector is to run. We put the function in its own module to
minimize the imports that the new process must perform to run the function.
"""


import logging
import random
import time
        
from vesper.command.job_logging_manager import JobLoggingManager
import vesper.util.django_utils as django_utils

        
def run_detector(detector_id, recording_file_id, channel_num, logging_info):
        
    # Set up Django for the new process.
    django_utils.set_up_django()
    
    from vesper.django.app.models import Processor, RecordingFile
    
    detector = Processor.objects.get(id=detector_id)
    recording_file = RecordingFile.objects.get(id=recording_file_id)
    
    logger = JobLoggingManager.create_logger(logging_info)
    
    logger.info('Running {} on {} channel {}...'.format(
        detector, recording_file, channel_num))
    
    duration = random.randint(1, 3)
    time.sleep(duration)
    
    logger.info('{} completed.'.format(detector))
    
    logging.shutdown()
    
