"""
Station-night sets for detector development.

Three station-night sets were used for developing the MPG Ranch Tseep
Detector and the MPG Ranch Thrush Detector, versions 0.0 and 1.0.

The three sets are called the *initial*, *validation*, and *test* sets.
The recordings of the initial set of station nights were used to evaluate
the MPG Ranch Detectors 0.0 (by manually coarse classifying the clips they
created when run on the recordings and plotting precision vs. number of
calls curves), and, based on the results of that evaluation, to provide
false positive noise examples for the dataset used to train the MPG Ranch
Detector 1.0. The validation and test sets were set aside for evaluating
the MPG Ranch Detector 1.0. Clips from the station-nights in the
validation and test sets are excluded from detector training sets in
order to make detector evaluations more informative.

The sets of station-nights in this module were created by the
`create_station_night_sets` script.
"""


import vesper.util.time_utils as time_utils


def _parse_station_nights(station_nights):
    return frozenset([
        _parse_station_night(line)
        for line in station_nights.strip().split('\n')
        if line.strip() != ''])
    
    
def _parse_station_night(line):
    
    # Split line into station name and night date.
    station, night = line.strip().split(' / ')
    
    # TODO: Use `datetime.date.fromisoformat` here when we no
    # longer need to support Python 3.6.
    yyyy, mm, dd = night.split('-')
    night = time_utils.parse_date(yyyy, mm, dd)
    
    return station, night


INITIAL_STATION_NIGHTS = _parse_station_nights('''

    Angel / 2018-08-28
    Bear / 2018-08-20
    Bell Crossing / 2018-08-25
    Bivory / 2018-08-20
    CB Ranch / 2018-08-02
    Coki / 2018-08-10
    Cricket / 2018-08-31
    Darby High School PC / 2018-08-09
    Dashiell / 2018-08-17
    Deer Mountain Lookout / 2018-08-30
    DonnaRae / 2018-08-16
    Dreamcatcher / 2018-08-19
    Esmerelda / 2018-08-14
    Evander / 2018-08-22
    Florence High School / 2018-08-02
    Grandpa's Pond / 2018-08-16
    Heron Crossing / 2018-08-12
    IBO Lucky Peak / 2018-08-17
    IBO River / 2018-08-31
    JJ / 2018-08-14
    KBK / 2018-08-20
    Kate / 2018-08-28
    Lee Metcalf NWR / 2018-08-24
    Lilo / 2018-08-30
    Lost Trail / 2018-08-30
    MPG North / 2018-08-07
    MPG Ranch Floodplain SM2 / 2018-08-17
    MPG Ranch Ridge / 2018-08-05
    MPG Ranch Sheep Camp / 2018-08-10
    MPG Ranch Subdivision / 2018-08-05
    MPG Ranch Zumwalt Ridge / 2018-08-25
    Max / 2018-08-17
    Meadowlark / 2018-08-20
    Mickey / 2018-08-26
    Mitzi / 2018-08-09
    Molly / 2018-08-30
    Oxbow / 2018-08-18
    Panda / 2018-08-30
    Petey / 2018-08-26
    Pocket Gopher / 2018-08-12
    Sadie-Kate / 2018-08-20
    Sasquatch / 2018-08-29
    Seeley High School / 2018-08-05
    Sleeman / 2018-08-23
    Slocum / 2018-08-06
    St Mary Lookout / 2018-08-18
    Sula Peak Lookout / 2018-08-12
    Sula Ranger Station / 2018-08-10
    Teller / 2018-08-02
    Walnut / 2018-08-24
    Willow Mountain Lookout / 2018-08-16
    YVAS / 2018-08-14
    Zuri / 2018-08-03
    
    Angel / 2018-09-28
    Bear / 2018-09-13
    Bell Crossing / 2018-09-25
    Bivory / 2018-09-14
    CB Ranch / 2018-09-02
    Coki / 2018-09-09
    Cricket / 2018-09-17
    Darby High School PC / 2018-09-29
    Dashiell / 2018-09-22
    Deer Mountain Lookout / 2018-09-11
    DonnaRae / 2018-09-16
    Dreamcatcher / 2018-09-13
    Esmerelda / 2018-09-10
    Evander / 2018-09-16
    Florence High School / 2018-09-19
    Grandpa's Pond / 2018-09-12
    Heron Crossing / 2018-09-30
    IBO Lucky Peak / 2018-09-28
    IBO River / 2018-09-29
    JJ / 2018-09-02
    KBK / 2018-09-17
    Kate / 2018-09-05
    Lee Metcalf NWR / 2018-09-10
    Lilo / 2018-09-05
    Lost Trail / 2018-09-28
    MPG North / 2018-09-25
    MPG Ranch Floodplain / 2018-09-11
    MPG Ranch Ridge / 2018-09-20
    MPG Ranch Sheep Camp / 2018-09-21
    MPG Ranch Subdivision / 2018-09-07
    Max / 2018-09-04
    Meadowlark / 2018-09-30
    Mickey / 2018-09-26
    Mitzi / 2018-09-09
    Molly / 2018-09-30
    Oxbow / 2018-09-18
    Panda / 2018-09-23
    Petey / 2018-09-13
    Pocket Gopher / 2018-09-28
    Sasquatch / 2018-09-04
    Seeley High School / 2018-09-10
    Sleeman / 2018-09-29
    Slocum / 2018-09-05
    St Mary Lookout / 2018-09-08
    Sula Peak Lookout / 2018-09-10
    Sula Ranger Station / 2018-09-04
    Teller / 2018-09-16
    Walnut / 2018-09-30
    Willow Mountain Lookout / 2018-09-08
    YVAS / 2018-09-23
    Zuri / 2018-09-03
    
''')


VALIDATION_STATION_NIGHTS = _parse_station_nights('''

    Angel / 2018-08-17
    Bear / 2018-08-09
    Bell Crossing / 2018-08-01
    Bivory / 2018-08-31
    CB Ranch / 2018-08-18
    Coki / 2018-08-12
    Cricket / 2018-08-14
    Darby High School PC / 2018-08-28
    Dashiell / 2018-08-23
    Deer Mountain Lookout / 2018-08-10
    DonnaRae / 2018-08-04
    Dreamcatcher / 2018-08-29
    Esmerelda / 2018-08-28
    Evander / 2018-08-25
    Florence High School / 2018-08-17
    Grandpa's Pond / 2018-08-30
    Heron Crossing / 2018-08-15
    IBO Lucky Peak / 2018-08-27
    IBO River / 2018-08-23
    JJ / 2018-08-11
    KBK / 2018-08-10
    Kate / 2018-08-18
    Lee Metcalf NWR / 2018-08-19
    Lilo / 2018-08-13
    Lost Trail / 2018-08-05
    MPG North / 2018-08-11
    MPG Ranch Floodplain SM2 / 2018-08-20
    MPG Ranch Ridge / 2018-08-23
    MPG Ranch Sheep Camp / 2018-08-29
    MPG Ranch Subdivision / 2018-08-18
    MPG Ranch Zumwalt Ridge / 2018-08-20
    Max / 2018-08-26
    Meadowlark / 2018-08-08
    Mickey / 2018-08-09
    Mitzi / 2018-08-02
    Molly / 2018-08-22
    Oxbow / 2018-08-07
    Panda / 2018-08-24
    Petey / 2018-08-20
    Pocket Gopher / 2018-08-16
    Sadie-Kate / 2018-08-11
    Sasquatch / 2018-08-19
    Seeley High School / 2018-08-20
    Sleeman / 2018-08-08
    Slocum / 2018-08-24
    St Mary Lookout / 2018-08-15
    Sula Peak Lookout / 2018-08-31
    Sula Ranger Station / 2018-08-31
    Teller / 2018-08-13
    Walnut / 2018-08-07
    Willow Mountain Lookout / 2018-08-17
    YVAS / 2018-08-02
    Zuri / 2018-08-13

    Angel / 2018-09-30
    Bear / 2018-09-09
    Bell Crossing / 2018-09-20
    Bivory / 2018-09-05
    CB Ranch / 2018-09-23
    Coki / 2018-09-19
    Cricket / 2018-09-12
    Darby High School PC / 2018-09-11
    Dashiell / 2018-09-11
    Deer Mountain Lookout / 2018-09-16
    DonnaRae / 2018-09-23
    Dreamcatcher / 2018-09-25
    Esmerelda / 2018-09-08
    Evander / 2018-09-07
    Florence High School / 2018-09-20
    Grandpa's Pond / 2018-09-08
    Heron Crossing / 2018-09-04
    IBO Lucky Peak / 2018-09-13
    IBO River / 2018-09-09
    JJ / 2018-09-04
    KBK / 2018-09-11
    Kate / 2018-09-25
    Lee Metcalf NWR / 2018-09-02
    Lilo / 2018-09-12
    Lost Trail / 2018-09-03
    MPG North / 2018-09-12
    MPG Ranch Floodplain / 2018-09-30
    MPG Ranch Ridge / 2018-09-10
    MPG Ranch Sheep Camp / 2018-09-14
    MPG Ranch Subdivision / 2018-09-02
    Max / 2018-09-20
    Meadowlark / 2018-09-26
    Mickey / 2018-09-14
    Mitzi / 2018-09-06
    Molly / 2018-09-24
    Oxbow / 2018-09-09
    Panda / 2018-09-08
    Petey / 2018-09-12
    Pocket Gopher / 2018-09-20
    Sasquatch / 2018-09-30
    Seeley High School / 2018-09-14
    Sleeman / 2018-09-13
    Slocum / 2018-09-10
    St Mary Lookout / 2018-09-05
    Sula Peak Lookout / 2018-09-03
    Sula Ranger Station / 2018-09-14
    Teller / 2018-09-07
    Walnut / 2018-09-01
    Willow Mountain Lookout / 2018-09-01
    YVAS / 2018-09-18
    Zuri / 2018-09-20

''')


TEST_STATION_NIGHTS = _parse_station_nights('''

    Angel / 2018-08-25
    Bear / 2018-08-14
    Bell Crossing / 2018-08-31
    Bivory / 2018-08-09
    CB Ranch / 2018-08-23
    Coki / 2018-08-17
    Cricket / 2018-08-04
    Darby High School PC / 2018-08-08
    Dashiell / 2018-08-21
    Deer Mountain Lookout / 2018-08-06
    DonnaRae / 2018-08-30
    Dreamcatcher / 2018-08-26
    Esmerelda / 2018-08-08
    Evander / 2018-08-26
    Florence High School / 2018-08-15
    Grandpa's Pond / 2018-08-18
    Heron Crossing / 2018-08-23
    IBO Lucky Peak / 2018-08-13
    IBO River / 2018-08-08
    JJ / 2018-08-31
    KBK / 2018-08-13
    Kate / 2018-08-27
    Lee Metcalf NWR / 2018-08-23
    Lilo / 2018-08-11
    Lost Trail / 2018-08-06
    MPG North / 2018-08-28
    MPG Ranch Floodplain SM2 / 2018-08-04
    MPG Ranch Ridge / 2018-08-12
    MPG Ranch Sheep Camp / 2018-08-14
    MPG Ranch Subdivision / 2018-08-26
    MPG Ranch Zumwalt Ridge / 2018-08-16
    Max / 2018-08-20
    Meadowlark / 2018-08-22
    Mickey / 2018-08-11
    Mitzi / 2018-08-25
    Molly / 2018-08-21
    Oxbow / 2018-08-10
    Panda / 2018-08-16
    Petey / 2018-08-28
    Pocket Gopher / 2018-08-23
    Sadie-Kate / 2018-08-10
    Sasquatch / 2018-08-23
    Seeley High School / 2018-08-19
    Sleeman / 2018-08-07
    Slocum / 2018-08-30
    St Mary Lookout / 2018-08-26
    Sula Peak Lookout / 2018-08-16
    Sula Ranger Station / 2018-08-03
    Teller / 2018-08-18
    Walnut / 2018-08-11
    Willow Mountain Lookout / 2018-08-06
    YVAS / 2018-08-07
    Zuri / 2018-08-19

    Angel / 2018-09-22
    Bear / 2018-09-08
    Bell Crossing / 2018-09-19
    Bivory / 2018-09-15
    CB Ranch / 2018-09-15
    Coki / 2018-09-14
    Cricket / 2018-09-13
    Darby High School PC / 2018-09-17
    Dashiell / 2018-09-25
    Deer Mountain Lookout / 2018-09-23
    DonnaRae / 2018-09-03
    Dreamcatcher / 2018-09-07
    Esmerelda / 2018-09-18
    Evander / 2018-09-12
    Florence High School / 2018-09-26
    Grandpa's Pond / 2018-09-22
    Heron Crossing / 2018-09-28
    IBO Lucky Peak / 2018-09-12
    IBO River / 2018-09-12
    JJ / 2018-09-03
    KBK / 2018-09-06
    Kate / 2018-09-14
    Lee Metcalf NWR / 2018-09-24
    Lilo / 2018-09-30
    Lost Trail / 2018-09-10
    MPG North / 2018-09-05
    MPG Ranch Floodplain / 2018-09-07
    MPG Ranch Ridge / 2018-09-14
    MPG Ranch Sheep Camp / 2018-09-20
    MPG Ranch Subdivision / 2018-09-15
    Max / 2018-09-27
    Meadowlark / 2018-09-27
    Mickey / 2018-09-22
    Mitzi / 2018-09-24
    Molly / 2018-09-27
    Oxbow / 2018-09-22
    Panda / 2018-09-01
    Petey / 2018-09-11
    Pocket Gopher / 2018-09-07
    Sasquatch / 2018-09-20
    Seeley High School / 2018-09-13
    Sleeman / 2018-09-05
    Slocum / 2018-09-21
    St Mary Lookout / 2018-09-06
    Sula Peak Lookout / 2018-09-17
    Sula Ranger Station / 2018-09-01
    Teller / 2018-09-22
    Walnut / 2018-09-06
    Willow Mountain Lookout / 2018-09-05
    YVAS / 2018-09-19
    Zuri / 2018-09-24

''')


NON_TRAINING_STATION_NIGHTS = VALIDATION_STATION_NIGHTS | TEST_STATION_NIGHTS
    
    
def _main():
    
    _check_disjointness(INITIAL_STATION_NIGHTS, VALIDATION_STATION_NIGHTS)
    _check_disjointness(VALIDATION_STATION_NIGHTS, TEST_STATION_NIGHTS)
    _check_disjointness(TEST_STATION_NIGHTS, INITIAL_STATION_NIGHTS)
    print('Initial, validation, and test sets are mutually disjoint.')
    
    non_training_station_nights = sorted(NON_TRAINING_STATION_NIGHTS)
    for station_night in non_training_station_nights:
        print(station_night)
    
    
def _check_disjointness(a, b):
    intersection = a & b
    if len(intersection) != 0:
        raise ValueError(
            'Set intersection {} is not empty.'.format(intersection))
        
        
if __name__ == '__main__':
    _main()
