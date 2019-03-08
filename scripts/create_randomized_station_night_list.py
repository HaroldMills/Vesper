'''
Script that creates a randomized list of station/night pairs.

Given a list of station names and a list of night dates, this script
writes a semi-randomized list of the elements of the cartesian product
of the two lists to a CSV file. The station names cycle through an
alphabetized version of the input station names list, while for each
station the input night dates appear in a randomly shuffled order that
is (probably) different for each station.
'''


import calendar
import csv
import itertools
import random


STATION_NAMES = sorted('''
Angela
Bear
Bell Crossing
Darby
Dashiell
Davies
Deer Mountain
Floodplain
Florence
KBK
Lilo
MPG North
Nelson
Oxbow
Powell
Reed
Ridge
Seeley
Sheep Camp
St Mary
Sula Peak
Teller
Troy
Walnut
Weber
Willow
'''.strip().split('\n'))

YEAR_MONTH_PAIRS = [(2017, 8), (2017, 9)]

OUTPUT_FILE_PATH = '/Users/harold/Desktop/Station-Nights.csv'


def main():
    
    # Seed random number generation so we get the same output every time
    # we run this script.
    random.seed(0)
    
    station_nights = get_station_nights()
    
    write_csv_file(station_nights)
    
    
def get_station_nights():
    
    dates = get_dates()
    
    station_night_rows = [
        get_station_night_list(n, dates) for n in STATION_NAMES]
        
    station_night_columns = zip(*station_night_rows)
    
    return itertools.chain.from_iterable(station_night_columns)
    
    
def get_station_night_list(station_name, dates):
    dates = random.sample(dates, len(dates))
    return [(station_name, d) for d in dates]
            
    
def get_dates():
    date_lists = [get_dates_aux(*p) for p in YEAR_MONTH_PAIRS]
    return list(itertools.chain.from_iterable(date_lists))


def get_dates_aux(year, month):
    num_days = calendar.monthrange(year, month)[1]
    prefix = '{:d}-{:02d}-'.format(year, month)
    f = prefix + '{:02d}'
    return [f.format(d) for d in range(1, num_days + 1)]
    
    
def write_csv_file(station_nights):
    with open(OUTPUT_FILE_PATH, 'w') as csv_file:
        writer = csv.writer(csv_file)
        writer.writerow(('Station', 'Night'))
        for pair in station_nights:
            writer.writerow(pair)
    
    
if __name__ == '__main__':
    main()
