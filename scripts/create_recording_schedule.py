"""
Script that creates a recording schedule.

To use this script:

    1. Change the values of the variables below that have all-caps names
       (LAT, LON, etc., all near the top of the file) for your use.
       
    2. At an operating system command prompt, change to the directory
       containing this script and then run the script with the command:

           python create_recording_schedule.py
           
       With the default value of OUTPUT_FILE_PATH below, the script will
       write its output to the file Schedule.csv in the same directory.
"""


import datetime

import pytz

from vesper.ephem.sun_moon import SunMoon
import vesper.util.os_utils as os_utils
import vesper.util.time_utils as time_utils



# latitude in degrees north
LAT = 46.641042

# longitude in degrees east
LON = -114.076499

# start night (arguments to datetime.date function are year, month, and day)
START_NIGHT = datetime.date(2015, 8, 20)

# end night (arguments to datetime.date function are year, month, and day)
END_NIGHT = datetime.date(2015, 10, 30)

# sunset offset in minutes
SUNSET_OFFSET = -30

# sunrise offset in minutes
SUNRISE_OFFSET = 30

# Time zone name. Note that if you specify the name of a time zone in which
# DST is observed, the times output by the script will reflect DST-related
# time changes. If this isn't what you want, choose the name of a time
# zone with the appropriate UTC offset in which DST is not observed. You
# can see a list of Olson database time zones, including both their names
# (any of which should work below) and UTC offsets, at:
#
#     https://en.wikipedia.org/wiki/List_of_tz_database_time_zones
#
# For example, if you'd like a time zone that's six hours behind UTC
# (like MDT) in which DST is not observed, you can choose 'Pacific/Galapagos'.
TIME_ZONE = pytz.timezone('US/Mountain')

OUTPUT_FILE_PATH = 'Schedule.csv'

ONE_DAY = datetime.timedelta(days=1)


def main():
    
    sun_moon = SunMoon(LAT, LON, TIME_ZONE, result_times_local=True)
    
    night = START_NIGHT
    sunset_offset = datetime.timedelta(minutes=SUNSET_OFFSET)
    sunrise_offset = datetime.timedelta(minutes=SUNRISE_OFFSET)
    
    lines = ['Night,Start Time,End Time']
    
    while night <= END_NIGHT:
        
        start_time = _get_time(sun_moon, night, 'Sunset', sunset_offset)
        end_time = _get_time(sun_moon, night, 'Sunrise', sunrise_offset)
                
        line = f'{str(night)},{start_time},{end_time}'
        lines.append(line)
        
        night += ONE_DAY
        
    text = ''.join(line + '\n' for line in lines)
    os_utils.write_file(OUTPUT_FILE_PATH, text)


def _get_time(sun_moon, night, event_name, offset):
    time = sun_moon.get_solar_event_time(night, event_name, day=False)
    time += offset
    time = time_utils.round_datetime(time, 60)
    return time.strftime('%Y-%m-%d %H:%M')


if __name__ == '__main__':
    main()
