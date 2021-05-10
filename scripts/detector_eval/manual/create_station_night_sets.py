"""
Script that chooses sets of station-nights for detector evaluation.

For each station in the archive of the directory in which this script is
run, the script randomly chooses initial, validation, and test nights for
the station and the month specified by `MONTH_NUM`. The script prints
the resulting station-night sets to the standard output.

See the `station_night_sets` module for more about the three station-night
sets.
"""


from collections import defaultdict
import random

# Set up Django. This must happen before any use of Django, including
# ORM class imports.
import vesper.util.django_utils as django_utils
django_utils.set_up_django()

from vesper.django.app.models import Recording


MONTH_NUM = 9
"""Month for which to choose recordings."""


def main():
    
    # Seed random number generator to make recording choices reproducible.
    random.seed(0)
    
    night_sets = get_night_sets()
    
    initial_station_nights = choose_initial_station_nights(night_sets)
    
    val_station_nights, test_station_nights = \
        choose_val_and_test_station_nights(night_sets, initial_station_nights)
        
    show_station_nights('Initial', initial_station_nights)
    show_station_nights('Validation', val_station_nights)
    show_station_nights('Test', test_station_nights)
    
    
def get_night_sets():
    
    """
    Gets a mapping from station names to sets of nights for which there
    are recordings.
    """

    night_sets = defaultdict(set)
    
    for recording in Recording.objects.all():
        station_name, night = get_recording_info(recording)
        if night.month == MONTH_NUM:
            night_sets[station_name].add(night)
        
    return night_sets
        
        
def get_recording_info(recording):
    station = recording.station
    night = station.get_night(recording.start_time)
    return station.name, night


def choose_initial_station_nights(night_sets):
    
    station_nights = set()
    
    for station_name in night_sets.keys():
        
        nights = night_sets[station_name]
        
        # Sort nights before choosing to make the choice reproducible
        # across runs of this script.
        nights = sorted(nights)
        
        if len(nights) != 0:
            # there is at least one recording for this station and month
            
            night = random.choice(nights)
            station_nights.add((station_name, night))
            
    return station_nights
           
    
def choose_val_and_test_station_nights(night_sets, initial_station_nights):
    
    initial_station_nights = dict(initial_station_nights)
    val_station_nights = set()
    test_station_nights = set()
    
    for station_name in night_sets.keys():
        
        # Copy night set for this station.
        nights = set(night_sets[station_name])
        
        # Remove night that was chosen for initial station-night set.
        night = initial_station_nights.get(station_name)
        if night is not None:
            nights.remove(night)
        
        # Sort remaining nights to make choices reproducible across
        # runs of this script.
        nights = sorted(nights)
        
        # Shuffle nights to make subsequent choices pseudo-random.
        random.shuffle(nights)
        
        # Choose validation night.
        if len(nights) >= 1:
            val_station_nights.add((station_name, nights[0]))
            
        # Choose test night.
        if len(nights) >= 2:
            test_station_nights.add((station_name, nights[1]))
            
    return val_station_nights, test_station_nights
        
        
def show_station_nights(name, station_nights):
    print('{} station-nights:'.format(name))
    station_nights = sorted(station_nights)
    for station_name, night in station_nights:
        print('    {} / {}'.format(station_name, str(night)))
        
        
if __name__ == '__main__':
    main()
