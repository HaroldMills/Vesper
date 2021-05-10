"""
Script that deletes Old Bird detector clips that have no start indices.

The original Old Bird detectors include only approximate start times in
the names of the clip files they create. To find the precise start time
of a clip in its parent recording we must search for the samples of the
clip in the recording. Sometimes, however, this process fails, for example
if the clip is too short, so that there are multiple copies of it in the
recording (for some reason the Old Bird detectors sometimes create very
short clips, e.g. comprising only a single sample), or if multiple
Old Bird detection jobs were run at once, causing some clips to be
attributed to the wrong recordings. This script deletes from an archive
clips that could not be located in their parent recordings.
"""


from django.db import transaction

# Set up Django. This must happen before any use of Django, including
# ORM class imports.
import vesper.util.django_utils as django_utils
django_utils.set_up_django()

from vesper.django.app.models import Clip, Processor


DETECTOR_NAMES = frozenset([
    'Old Bird Thrush Detector',
    'Old Bird Tseep Detector'
])

DRY_RUN = False


def main():
    
    with transaction.atomic():
        
        for processor in Processor.objects.all():
            
            if processor.name in DETECTOR_NAMES:
                
                print(f'Getting clips for detector "{processor.name}"...')
                
                clips = Clip.objects.filter(
                    creating_processor_id=processor.id, start_index=None)
                 
                print(
                    f'Deleting {clips.count()} clips for detector '
                    f'"{processor.name}"...')
                 
                if not DRY_RUN:
                    clips.delete()
                    
    print('Done.')

 
if __name__ == '__main__':
    main()
