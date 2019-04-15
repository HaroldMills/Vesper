"""
Script that prunes the recordings of an archive.

For each station in the archive of the directory in which this script is
run, and each of the months specified by the `MONTH_NUMS` module attribute,
the script randomly chooses one night for the station and month for which
there is at least one recording (if there are any such nights) and deletes
all recordings for the station and month for all other nights. For each
station and month, this leaves only the recordings for the chosen night.
"""


from collections import defaultdict
import os
import random


# Set up Django.
os.environ['DJANGO_SETTINGS_MODULE'] = 'vesper.django.project.settings'
import django
django.setup()

from vesper.django.app.models import Recording


MONTH_NUMS = [9]
"""
Numbers of the months for which to retain recordings.

For each station that has recordings for one or more nights of a specified
month, the recordings for one randomly chosen night of the month are
retained but the recordings for all other nights of the month are deleted.
"""


def main():
    
    # Seed random number generator to make recording choices reproducible.
    random.seed(0)
    
    night_sets = get_night_sets()
    
    retained_station_nights = choose_station_nights(night_sets, MONTH_NUMS)
    
    show_station_nights(retained_station_nights)
    
    # Be careful about uncommenting the following line!
    # delete_recordings(retained_station_nights)
        
    
def get_night_sets():
    
    """
    Gets a mapping from station names to sets of nights for which there
    are recordings.
    """

    night_sets = defaultdict(set)
    
    for recording in Recording.objects.all():
        station_name, night = get_recording_info(recording)
        night_sets[station_name].add(night)
        
    return night_sets
        
        
def get_recording_info(recording):
    station = recording.station
    night = station.get_night(recording.start_time)
    return station.name, night


def choose_station_nights(night_sets, month_nums):
    
    station_nights = set()
    
    for station_name in night_sets.keys():
        
        nights = night_sets[station_name]
        
        for month_num in month_nums:
            
            # We sort the nights before choosing to make the choice
            # reproducible across runs of this script.
            month_nights = sorted(n for n in nights if n.month == month_num)
            
            if len(month_nights) != 0:
                # there is at least one recording for this station and month
                
                night = random.choice(month_nights)
                station_nights.add((station_name, night))
            
    return station_nights
           
    
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
        
        info = get_recording_info(recording)
        
        if info not in retained_station_nights:
            
            print('deleting recording "{}"...'.format(recording))
            recording.delete()
            
            num_deleted += 1
            
        num_recordings += 1
        
    print('Deleted {} and retained {} of {} recordings.'.format(
        num_deleted, num_recordings - num_deleted, num_recordings))

    
if __name__ == '__main__':
    main()
