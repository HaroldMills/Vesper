"""
Script that classifies unclassified clips of an archive as noises.

The script classifies all unclassified clips of the detectors whose
names are in `DETECTOR_NAMES`.
"""


import os

import vesper.util.time_utils as time_utils


# Set up Django.
os.environ['DJANGO_SETTINGS_MODULE'] = 'vesper.django.project.settings'
import django
django.setup()

from django.db import transaction

from vesper.django.app.models import (
    AnnotationInfo, Clip, Processor, StringAnnotation, StringAnnotationEdit,
    User)


DETECTOR_NAMES = frozenset([
    'BirdVoxDetect 0.1.a0 AT 05',
    'MPG Ranch Thrush Detector 0.0 40',
    'MPG Ranch Tseep Detector 0.0 40'
])

USER_NAME = 'Harold'
ANNOTATION_NAME = 'Classification'
CLASSIFICATION = 'Noise'


def main():
    
    annotation_info = AnnotationInfo.objects.get(name=ANNOTATION_NAME)
    user = User.objects.get(username=USER_NAME)

    for processor in Processor.objects.all():
        
        if processor.name in DETECTOR_NAMES:
            
            print('{}...'.format(processor.name))
            
            clips = get_unclassified_clips(processor, annotation_info)
            
            classify_clips(clips, user, annotation_info, CLASSIFICATION)
            
            
def get_unclassified_clips(processor, annotation_info):
    clips = Clip.objects.filter(creating_processor_id=processor.id)
    return clips.exclude(string_annotation__info=annotation_info)
            
            
@transaction.atomic
def classify_clips(clips, user, annotation_info, classification):
    
    count = 0
    
    for clip in clips:
    
        creation_time = time_utils.get_utc_now()
        
        kwargs = {
            'value': classification,
            'creation_time': creation_time,
            'creating_user': user,
            'creating_job': None,
            'creating_processor': None
        }
    
        StringAnnotation.objects.create(
            clip=clip,
            info=annotation_info,
            **kwargs)
             
        StringAnnotationEdit.objects.create(
            clip=clip,
            info=annotation_info,
            action=StringAnnotationEdit.ACTION_SET,
            **kwargs)

        count += 1
        if count % 10000 == 0:
            print('    {}...'.format(count))

 
if __name__ == '__main__':
    main()
