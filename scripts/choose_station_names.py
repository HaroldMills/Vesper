"""Script that chooses a random subset of a set of station names."""


import random


def create_set(s):
    return set(s.strip().split('\n'))


ALL_STATION_NAMES = create_set('''
Angel
Bear
Bell Crossing
Bivory
CB Ranch
Coki
Cricket
Darby High School PC
Darby High School Swift
Dashiell
Deer Mountain Lookout
DonnaRae
Dreamcatcher
Esmerelda
Evander
Florence High School
Grandpa's Pond
Heron Crossing
IBO Lucky Peak
IBO River
JJ
KBK
Kate
Lee Metcalf NWR
Lilo
Lost Trail
MPG North
MPG Ranch Floodplain SM2
MPG Ranch Floodplain Swift
MPG Ranch Ridge
MPG Ranch Sheep Camp
MPG Ranch Subdivision
MPG Ranch Zumwalt Ridge
Max
Meadowlark
Mickey
Mitzi
Molly
Oxbow
Panda
Petey
Pocket Gopher
Sadie-Kate
Sasquatch
Seeley High School
Sleeman
Slocum
St Mary Lookout
Sula Peak Lookout
Sula Ranger Station
Teller
Walnut
Willow Mountain Lookout
YVAS
Zuri
''')

REQUIRED_STATION_NAMES = create_set('''
MPG Ranch Floodplain SM2
Meadowlark
Oxbow
''')

IGNORED_STATION_NAMES = create_set('''
MPG Ranch Floodplain Swift
''')

DESIRED_NUM_STATIONS = 12


def main():
    
    station_names = \
        ALL_STATION_NAMES - REQUIRED_STATION_NAMES - IGNORED_STATION_NAMES
    
    k = DESIRED_NUM_STATIONS - len(REQUIRED_STATION_NAMES)
    station_names = random.sample(station_names, k)
    
    station_names = sorted(set(station_names) | REQUIRED_STATION_NAMES)
    
    for name in station_names:
        print(name)
    
    
if __name__ == '__main__':
    main()
