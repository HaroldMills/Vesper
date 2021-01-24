from pathlib import Path
import datetime
import sys

import pytz


TIME_ZONE = pytz.timezone('US/Eastern')


def main():
    
    station_name = sys.argv[1]
    dir_path = Path(sys.argv[2])
    
    file_paths = sorted(dir_path.glob('*.WAV'))
    
    for file_path in file_paths:
        move_file(file_path, station_name)


def move_file(file_path, station_name):
    
    recorder_name = file_path.parent.parent.name
    file_name = file_path.name
    
    start_time = parse_file_name(file_name)
    night = get_night(start_time)
    
    night_dir_name = night.strftime('%Y-%m-%d')
    start_time_string = start_time.strftime('%Y-%m-%d_%H.%M.%S_Z')
    new_file_name = f'{station_name}_{recorder_name}_{start_time_string}.wav'
    
    night_dir_path = file_path.parent / night_dir_name
    night_dir_path.mkdir(mode=0o755, parents=True, exist_ok=True)
    
    new_file_path = night_dir_path / new_file_name
    file_path.rename(new_file_path)
    
    print(f'{start_time} {night_dir_path} {new_file_path}')
    
    
def parse_file_name(file_name):
    start_time = datetime.datetime.strptime(file_name, '%Y%m%d_%H%M%S.WAV')
    return pytz.utc.localize(start_time)


def get_night(dt):
    
    dt = dt.astimezone(TIME_ZONE)
    
    date = dt.date()
    hour = dt.hour
    
    if hour >= 12:
        return date
    
    else:
        return datetime.date.fromordinal(dt.toordinal() - 1)


if __name__ == '__main__':
    main()
