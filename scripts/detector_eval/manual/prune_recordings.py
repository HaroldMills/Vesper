"""
Script that prunes the recordings of an archive.

For the set of station-nights assigned to `retained_station_nights`
in the `main` function of this script, the script deletes from the
archive of the directory in which it is run all recordings for all
other station nights, leaving only the recordings of the specified
station-nights.
"""


import scripts.detector_eval.manual.station_night_sets as station_night_sets

# Set up Django. This must happen before any use of Django, including
# ORM class imports.
import vesper.util.django_utils as django_utils
django_utils.set_up_django()

from vesper.django.app.models import Recording


def main():
    
    retained_station_nights = station_night_sets.VALIDATION_STATION_NIGHTS
    
    show_station_nights(retained_station_nights)
    
    # Be careful about uncommenting the following line!
    delete_recordings(retained_station_nights)
        
    
def show_station_nights(station_nights):
    station_nights = sorted(station_nights)
    for station_name, night in station_nights:
        print('{} / {}'.format(station_name, str(night)))
        
        
def delete_recordings(retained_station_nights):
    
    num_recordings = 0
    num_deleted = 0
    
    for recording in Recording.objects.all():
        
        # if recording.station.name != 'Angel':
        #     continue
        
        station_night = get_recording_station_night(recording)
        
        if station_night not in retained_station_nights:
            
            print('deleting recording "{}"...'.format(recording))
            recording.delete()
            
            num_deleted += 1
            
        num_recordings += 1
        
    print('Deleted {} and retained {} of {} recordings.'.format(
        num_deleted, num_recordings - num_deleted, num_recordings))

    
def get_recording_station_night(recording):
    station = recording.station
    night = station.get_night(recording.start_time)
    return station.name, night


if __name__ == '__main__':
    main()
