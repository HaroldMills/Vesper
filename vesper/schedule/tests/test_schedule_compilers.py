import datetime

import pytz
import yaml

from vesper.schedule.schedule import Interval
from vesper.tests.test_case import TestCase
import vesper.schedule.schedule_compilers as schedule_compilers
import vesper.util.time_utils as time_utils


class _Context:
    
    def __init__(self, lat=None, lon=None, time_zone=None):
        self.lat = lat
        self.lon = lon
        self.time_zone = time_zone
        if self.time_zone is not None:
            self.time_zone = pytz.timezone(self.time_zone)
            
        
def _dt(year, month, day, hour=0, minute=0, second=0):
    dt = datetime.datetime(year, month, day, hour, minute, second)
    return pytz.utc.localize(dt)


class ScheduleParserTests(TestCase):
    
    
    def test_compile_interval_schedule(self):
        
        cases = (
            
            (
                '''
                    interval:
                        start: 2016-12-14 12:00:00
                        end: 2016-12-14 13:00:00
                ''',
                _Context(time_zone='US/Eastern'),
                (((2016, 12, 14, 17), (2016, 12, 14, 18), True),)
            ),
            
            (
                '''
                    interval:
                        start: 2016-12-14 noon
                        end: 2016-12-14 1 pm
                ''',
                _Context(time_zone='US/Eastern'),
                (((2016, 12, 14, 17), (2016, 12, 14, 18), True),)
            ),
            
            (
                '''
                    interval:
                        start: 2016-12-14 noon
                        duration: 1 hour
                ''',
                _Context(time_zone='US/Eastern'),
                (((2016, 12, 14, 17), (2016, 12, 14, 18), True),)
            ),
            
            (
                '''
                    interval:
                        end: 2016-12-14 1 pm
                        duration: 1 hour
                ''',
                _Context(time_zone='US/Eastern'),
                (((2016, 12, 14, 17), (2016, 12, 14, 18), True),)
            ),
            
            (
                '''
                    interval:
                        start: 2016-12-14 sunset
                        end: 2016-12-15 sunrise
                ''',
                _Context(lat=42.5, lon=-76.5),
                (((2016, 12, 14, 21, 34), (2016, 12, 15, 12, 29), False),)
            ),
            
            (
                '''
                    interval:
                        start: 2016-12-14 1 hour after sunset
                        end: 2016-12-15 30 minutes before sunrise
                ''',
                _Context(lat=42.5, lon=-76.5),
                (((2016, 12, 14, 22, 34), (2016, 12, 15, 11, 59), False),)
            ),
            
        )
        
        for spec, context, expected in cases:
            spec = yaml.load(spec)
            schedule = schedule_compilers.compile_interval_schedule(
                spec, context)
            self._assert_schedule(schedule, expected)
    
    
    def _assert_schedule(self, schedule, expected):
        actual_intervals = tuple(schedule.get_intervals())
        self.assertEqual(len(actual_intervals), len(expected))
        for i, actual_interval in enumerate(schedule.get_intervals()):
            expected_interval = _create_interval(expected[i][:2])
            exact = expected[i][2]
            if not exact:
                actual_interval = _round_interval(actual_interval)
            self.assertEqual(actual_interval, expected_interval)
        
        
    def test_compile_interval_schedule_spec_errors(self):
         
        cases = (
             
            # no properties
            '''
                interval:
            ''',
            
            # unrecognized property
            '''
                interval:
                    bobo: null
            ''',
            
            # bad start
            '''
                interval:
                    start: 2016-12-14
                    end: 2016-12-14 13:00:00
            ''',
        
            # bad end
            '''
                interval:
                    start: 2016-12-14 12:00:00
                    end: bobo
            ''',
        
            # bad duration
            '''
                interval:
                    start: 2016-12-14 12:00:00
                    duration: bobo
            ''',
            
            # start only
            '''
                interval:
                    start: 2016-12-14 12:00:00
            ''',
            
            # end only
            '''
                interval:
                    end: 2016-12-14 12:00:00
            ''',
            
            # duration only
            '''
                interval:
                    duration: 1 hour
            ''',
            
            # start, end, and duration
            '''
                interval:
                    start: 2016-12-14 12:00:00
                    end: 2016-12-14 13:00:00
                    duration: 1 hour
            '''
            
        )
        
        compile = schedule_compilers.compile_interval_schedule
        context = _Context(time_zone='US/Eastern')
        
        for spec in cases:
            spec = yaml.load(spec)
            self._assert_raises(ValueError, compile, spec, context)
        
        
    def test_compile_interval_schedule_context_errors(self):
         
        cases = (
            _Context(lat=42.5, lon=-76.5),
            _Context(lat=42.5, time_zone='US/Eastern'),
            _Context(lon=-76.5, time_zone='US/Eastern')
        )
        
        compile = schedule_compilers.compile_interval_schedule
        
        spec = yaml.load('''
            interval:
                start: 2016-12-14 12:00:00
                end: 2016-12-14 sunset
        ''')

        for context in cases:
            self._assert_raises(ValueError, compile, spec, context)
        
        
    def test_compile_intervals_schedule(self):
        
        cases = (
        
            (
                '''
                    intervals:
                    
                        - start: 2016-12-14 2 pm
                          end: 2016-12-14 3 pm
                          
                        - start: 2016-12-14 noon
                          end: 2016-12-14 13:00:00
                          
                        - start: 2016-12-14 sunset
                          end: 2016-12-15 sunrise
                          
                        - start: 2016-12-15 1 hour after sunset
                          end: 2016-12-16 30 minutes before sunrise
                ''',
                _Context(lat=42.5, lon=-76.5, time_zone='US/Eastern'),
                (((2016, 12, 14, 17), (2016, 12, 14, 18), True),
                 ((2016, 12, 14, 19), (2016, 12, 14, 20), True),
                 ((2016, 12, 14, 21, 34), (2016, 12, 15, 12, 29), False),
                 ((2016, 12, 15, 22, 34), (2016, 12, 16, 12, 0), False))
            ),
            
        )
        
        compile = schedule_compilers.compile_intervals_schedule
        
        for spec, context, expected in cases:
            spec = yaml.load(spec)
            schedule = compile(spec, context)
            self._assert_schedule(schedule, expected)

        
    def test_compile_daily_schedule(self):
        
        cases = (
            
            (
                '''
                    daily:
                        start_time: 5 pm
                        end_time: 6 pm
                        start_date: 2016-12-15
                        end_date: 2016-12-17
                ''',
                (((2016, 12, 15, 22), (2016, 12, 15, 23), True),
                 ((2016, 12, 16, 22), (2016, 12, 16, 23), True),
                 ((2016, 12, 17, 22), (2016, 12, 17, 23), True))
            ),
                  
            (
                '''
                    daily:
                        start_time: 5 pm
                        duration: 1 hour
                        start_date: 2016-12-15
                        end_date: 2016-12-17
                ''',
                (((2016, 12, 15, 22), (2016, 12, 15, 23), True),
                 ((2016, 12, 16, 22), (2016, 12, 16, 23), True),
                 ((2016, 12, 17, 22), (2016, 12, 17, 23), True))
            ),
                  
            (
                '''
                    daily:
                        end_time: 6 pm
                        duration: 1 hour
                        start_date: 2016-12-15
                        end_date: 2016-12-17
                ''',
                (((2016, 12, 15, 22), (2016, 12, 15, 23), True),
                 ((2016, 12, 16, 22), (2016, 12, 16, 23), True),
                 ((2016, 12, 17, 22), (2016, 12, 17, 23), True))
            ),
                
            # no time intervals  
            (
                '''
                    daily:
                        time_intervals: []
                        start_date: 2016-12-15
                        end_date: 2016-12-16
                ''',
                ()
            ),
                  
            (
                '''
                    daily:
                        time_intervals:
                            - start: 1 hour before sunrise
                              end: 1 hour after sunrise
                            - start: 5 pm
                              duration: 1 hour
                            - end: 8 pm
                              duration: 1 hour
                        start_date: 2016-12-15
                        end_date: 2016-12-16
                ''',
                (((2016, 12, 15, 11, 29), (2016, 12, 15, 13, 29), False),
                 ((2016, 12, 15, 22), (2016, 12, 15, 23), True),
                 ((2016, 12, 16, 0), (2016, 12, 16, 1), True),
                 ((2016, 12, 16, 11, 30), (2016, 12, 16, 13, 30), False),
                 ((2016, 12, 16, 22), (2016, 12, 16, 23), True),
                 ((2016, 12, 17, 0), (2016, 12, 17, 1), True))
            ),
                  
            # no date intervals
            (
                '''
                    daily:
                        start_time: 5 pm
                        duration: 1 hour
                        date_intervals: []
                ''',
                ()
            ),
                 
            (
                '''
                    daily:
                        start_time: 5 pm
                        duration: 1 hour
                        date_intervals:
                            - start: 2016-12-15
                              end: 2016-12-16
                            - start: 2016-12-20
                              end: 2016-12-21
                ''',
                (((2016, 12, 15, 22), (2016, 12, 15, 23), True),
                 ((2016, 12, 16, 22), (2016, 12, 16, 23), True),
                 ((2016, 12, 20, 22), (2016, 12, 20, 23), True),
                 ((2016, 12, 21, 22), (2016, 12, 21, 23), True))
            ),
                 
            # no time or date intervals
            (
                '''
                    daily:
                        time_intervals: []
                        date_intervals: []
                ''',
                ()
            ),
                  
            (
                '''
                    daily:
                        time_intervals:
                            - start: 5 am
                              duration: 1 hour
                            - start: 5 pm
                              duration: 1 hour
                        date_intervals:
                            - start: 2016-12-15
                              end: 2016-12-16
                            - start: 2016-12-20
                              end: 2016-12-21
                ''',
                (((2016, 12, 15, 10), (2016, 12, 15, 11), True),
                 ((2016, 12, 15, 22), (2016, 12, 15, 23), True),
                 ((2016, 12, 16, 10), (2016, 12, 16, 11), True),
                 ((2016, 12, 16, 22), (2016, 12, 16, 23), True),
                 ((2016, 12, 20, 10), (2016, 12, 20, 11), True),
                 ((2016, 12, 20, 22), (2016, 12, 20, 23), True),
                 ((2016, 12, 21, 10), (2016, 12, 21, 11), True),
                 ((2016, 12, 21, 22), (2016, 12, 21, 23), True))
            ),
                  
            # intervals out of order
            (
                '''
                    daily:
                        time_intervals:
                            - start: 5 pm
                              duration: 1 hour
                            - start: 5 am
                              duration: 1 hour
                        date_intervals:
                            - start: 2016-12-20
                              end: 2016-12-21
                            - start: 2016-12-15
                              end: 2016-12-16
                ''',
                (((2016, 12, 15, 10), (2016, 12, 15, 11), True),
                 ((2016, 12, 15, 22), (2016, 12, 15, 23), True),
                 ((2016, 12, 16, 10), (2016, 12, 16, 11), True),
                 ((2016, 12, 16, 22), (2016, 12, 16, 23), True),
                 ((2016, 12, 20, 10), (2016, 12, 20, 11), True),
                 ((2016, 12, 20, 22), (2016, 12, 20, 23), True),
                 ((2016, 12, 21, 10), (2016, 12, 21, 11), True),
                 ((2016, 12, 21, 22), (2016, 12, 21, 23), True))
            ),
                 
        )
        
        compile = schedule_compilers.compile_daily_schedule
        context = _Context(lat=42.5, lon=-76.5, time_zone='US/Eastern')

        for spec, expected in cases:
            spec = yaml.load(spec)
            schedule = compile(spec, context)
            self._assert_schedule(schedule, expected)
        
        
    def test_compile_daily_schedule_spec_errors(self):
         
        cases = (
             
            # no properties
            '''
               daily:
            ''',
            
            # unrecognized property
            '''
                daily:
                    bobo: null
            ''',
            
            # bad start time
            '''
                daily:
                    start_time: bobo
                    end_time: 6 pm
                    start_date: 2016-12-15
                    end_date: 2016-12-15
            ''',
            
            # bad start time (in time_invervals)
            '''
                daily:
                    time_intervals:
                        - start: booboo
                          end: 6 pm
                    start_date: 2016-12-15
                    end_date: 2016-12-15
            ''',
            
            # bad end time
            '''
                daily:
                    start_time: 5 pm
                    end_time: bobo
                    start_date: 2016-12-15
                    end_date: 2016-12-15
            ''',
            
            # bad duration
            '''
                daily:
                    start_time: 5 pm
                    duration: bobo
                    start_date: 2016-12-15
                    end_date: 2016-12-15
            ''',
            
            # bad start date
            '''
                daily:
                    start_time: 5 pm
                    end_time: 6 pm
                    start_date: bobo
                    end_date: 2016-12-15
            ''',
            
            # bad start date (in date_intervals)
            '''
                daily:
                    start_time: 5 pm
                    end_time: 6 pm
                    date_intervals:
                        - start: booboo
                          end: 2016-12-15
            ''',
            
            # bad end date
            '''
                daily:
                    start_time: 5 pm
                    end_time: 6 pm
                    start_date: 2016-12-15
                    end_date: bobo
            ''',
            
            # start time only
            '''
                daily:
                    start_time: 5 pm
                    start_date: 2016-12-15
                    end_date: 2016-12-15
            ''',
            
            # start time only (in time_intervals)
            '''
                daily:
                    time_intervals:
                        - start: 5 pm
                    start_date: 2016-12-15
                    end_date: 2016-12-15
            ''',
            
            # end time only
            '''
                daily:
                    end_time: 6 pm
                    start_date: 2016-12-15
                    end_date: 2016-12-15
            ''',
            
            # duration only
            '''
                daily:
                    duration: 1 hour
                    start_date: 2016-12-15
                    end_date: 2016-12-15
            ''',
            
            # start date only
            '''
                daily:
                    start_time: 5 pm
                    end_time: 6 pm
                    start_date: 2016-12-15
            ''',
            
            # start date only (in date_intervals)
            '''
                daily:
                    start_time: 5 pm
                    end_time: 6 pm
                    date_intervals:
                        - start: 2016-12-15
            ''',
            
            # end date only
            '''
                daily:
                    start_time: 5 pm
                    end_time: 6 pm
                    end_date: 2016-12-15
            ''',
            
            # start time, end time, and duration
            '''
                daily:
                    start_time: 5 pm
                    end_time: 6 pm
                    duration: 1 hour
                    start_date: 2016-12-15
                    end_date: 2016-12-15
            ''',
            
            # start time, end time, and duration (in time_intervals)
            '''
                daily:
                    time_intervals:
                        - start: 5 pm
                          end: 6 pm
                          duration: 1 hour
                    start_date: 2016-12-15
                    end_date: 2016-12-15
            ''',
            
        )
        
        compile = schedule_compilers.compile_daily_schedule
        context = _Context(time_zone='US/Eastern')
        
        for spec in cases:
            spec = yaml.load(spec)
            self._assert_raises(ValueError, compile, spec, context)
        
        
    def test_compile_daily_schedule_context_errors(self):
         
        specs = (
            
            '''
                daily:
                    start_time: sunrise
                    end_time: noon
                    start_date: 2016-12-15
                    end_date: 2016-12-17
            ''',
            
            '''
                daily:
                    time_intervals:
                        - start: sunrise
                          duration: 1 hour
                        - start: 5 pm
                          duration: 1 hour
                    start_date: 2016-12-15
                    end_date: 2016-12-17
            '''  
            
        )
        
        contexts = (
            _Context(lat=42.5, lon=-76.5),
            _Context(lat=42.5, time_zone='US/Eastern'),
            _Context(lon=-76.5, time_zone='US/Eastern')
        )
        
        compile = schedule_compilers.compile_daily_schedule
        
        for spec in specs:
            spec = yaml.load(spec)
            for context in contexts:
                self._assert_raises(ValueError, compile, spec, context)
        
        
    def test_compile_union_schedule(self):
        
        cases = (
            
            # union of zero schedules
            (
                '''
                    union: []
                ''',
                ()
            ),

            (
                '''
                    union:
                        - interval:
                              start: 2016-12-19 noon
                              duration: 1 hour
                        - intervals:
                              - start: 2016-12-20 noon
                                duration: 1 hour
                        - daily:
                              start_time: noon
                              duration: 1 hour
                              start_date: 2016-12-21
                              end_date: 2016-12-22
                        - union:
                            - interval:
                                  start: 2016-12-23 noon
                                  duration: 1 hour
                            - interval:
                                  start: 2016-12-24 noon
                                  duration: 1 hour
                ''',
                (((2016, 12, 19, 17), (2016, 12, 19, 18), True),
                 ((2016, 12, 20, 17), (2016, 12, 20, 18), True),
                 ((2016, 12, 21, 17), (2016, 12, 21, 18), True),
                 ((2016, 12, 22, 17), (2016, 12, 22, 18), True),
                 ((2016, 12, 23, 17), (2016, 12, 23, 18), True),
                 ((2016, 12, 24, 17), (2016, 12, 24, 18), True))
            ),
                 
        )
        
        compile = schedule_compilers.compile_union_schedule
        context = _Context(lat=42.5, lon=-76.5, time_zone='US/Eastern')

        for spec, expected in cases:
            spec = yaml.load(spec)
            schedule = compile(spec, context)
            self._assert_schedule(schedule, expected)
    
    
def _create_interval(interval):
    start, end = interval
    return Interval(_dt(*start), _dt(*end))


def _round_interval(interval):
    return tuple(time_utils.round_datetime(dt, 60) for dt in interval)


_NONOFFSET_TIME_CASES = (
    
    # time_24
    ('1:23:45', (1, 23, 45)),
    ('12:34:56', (12, 34, 56)),
    
    # hhmmss am_pm_time
    ('1:23:45 am', (1, 23, 45)),
    ('12:34:56 am', (0, 34, 56)),
    ('1:23:45 pm', (13, 23, 45)),
    ('12:34:56 pm', (12, 34, 56)),
    
    # hhmm am_pm_time
    ('1:23 am', (1, 23)),
    ('12:34 am', (0, 34)),
    ('1:23 pm', (13, 23)),
    ('12:34 pm', (12, 34)),
    
    # hh am_pm_time
    ('1 am', (1,)),
    ('12 am', (0,)),
    ('1 pm', (13,)),
    ('12 pm', (12,)),
    
    # time_name
    ('noon', (12,)),
    ('midnight', (0,))
    
)

_EVENT_NAMES = (
    'sunrise', 'sunset', 'civil dawn', 'civil dusk', 'nautical dawn',
    'nautical dusk', 'astronomical dawn', 'astronomical dusk')

_OFFSETS = (
    ('1:23:45', 5025),
    ('12:34:56', 45296),
    ('1 hour', 3600),
    ('1 hours', 3600),
    ('1.5 hours', 5400),
    ('.5 hours', 1800),
    ('1 minute', 60),
    ('1 minutes', 60),
    ('1.5 minutes', 90),
    ('.5 minutes', 30),
    ('1 second', 1),
    ('1 seconds', 1),
    ('1.5 seconds', 1.5),
    ('.5 seconds', .5)
)

_PREPOSITIONS = (
    ('before', -1),
    ('after', 1)
)

_BAD_TIMES = (
    
    # malformed
    '',
    'bobo',
    '0',
    '123',
    '1:23',
    '12:34',
    'morning time',
    'half past ten',
    
    # bad hhmmss times
    '1:23:99',
    '1:99:45',
    '99:23:45',
    
    # bad am/pm times
    '1:23:99 am',
    '1:99 pm',
    '0 am',
    
    # no event name
    '1 hour after',
    
    # unrecognized event name
    '1 hour after bobo',
    
    # unrecognized preposition
    '1 hour bobo sunset',
    
    # number other than 1 with plural units
    '2 hour after sunset',
    '2 minute after sunset',
    '2 second after sunset',
    
    # time with extra stuff at end
    '1:23:45 bobo',
    '1 hour after sunset bobo'
            
)


class LowLevelScheduleParserTests(TestCase):
    
    
    def test_parse_time_1(self):
        
        for s, args in _NONOFFSET_TIME_CASES:
            actual = schedule_compilers._parse_time(s)
            expected = datetime.time(*args)
            self.assertEqual(actual, expected)
            
        for event_name in _EVENT_NAMES:
            actual = schedule_compilers._parse_time(event_name)
            self._assert_solar_time(actual, event_name, 0)
            
            
    def test_parse_time_2(self):
        
        for event_name in _EVENT_NAMES:
            
            for offset, seconds in _OFFSETS:
                
                for preposition, factor in _PREPOSITIONS:
                    
                    time = '{} {} {}'.format(offset, preposition, event_name)
                    actual = schedule_compilers._parse_time(time)
                    
                    self._assert_solar_time(
                        actual, event_name, factor * seconds)
            
            
    def _assert_solar_time(self, time, event_name, offset):
        self.assertEqual(time.event_name, _capitalize(event_name))
        offset = datetime.timedelta(seconds=offset)
        self.assertEqual(time.offset, offset)
            
            
    def test_parse_time_errors(self):
        for s in _BAD_TIMES:
            actual = schedule_compilers._parse_time(s)
            self.assertIsNone(actual)
            
            
    def test_parse_date_time_1(self):
        
        for s, args in _NONOFFSET_TIME_CASES:
            actual = schedule_compilers._parse_date_time('2016-11-28 ' + s)
            expected = datetime.datetime(2016, 11, 28, *args)
            self.assertEqual(actual, expected)

        for event_name in _EVENT_NAMES:
            actual = schedule_compilers._parse_time(event_name)
            self._assert_solar_time(actual, event_name, 0)
            

    def test_parse_date_time_2(self):
        
        parse = schedule_compilers._parse_date_time
        date_string = '2016-11-28'
        date = datetime.date(2016, 11, 28)
        
        for event_name in _EVENT_NAMES:
            
            actual = parse(date_string + ' ' + event_name)
            self._assert_solar_date_time(actual, date, event_name, 0)
            
            for offset, seconds in _OFFSETS:
                
                for preposition, factor in _PREPOSITIONS:
                    
                    dt = '{} {} {} {}'.format(
                        date_string, offset, preposition, event_name)
                    actual = parse(dt)
                    
                    self._assert_solar_date_time(
                        actual, date, event_name, factor * seconds)


    def test_parse_date_time_errors(self):
        
        cases = (
            
            # empty
            '',
            
            # date only
            '2016-11-28',
            
            # time only
            '12:34:56',
            
            # malformed dates
            '2016-11-1 12:34:56',
            '2016-1-28 12:34:56',
            '201-11-28 12:34:56',
            
            # out-of-range date components
            '2016-11-99 12:34:56',
            '2016-99-28 12:34:56',
            '9999-11-99 12:34:56',
            
        )
        
        for s in cases:
            actual = schedule_compilers._parse_date_time(s)
            self.assertIsNone(actual)
            
        for s in _BAD_TIMES:
            actual = schedule_compilers._parse_date_time('2016-11-28 ' + s)
            self.assertIsNone(actual)

        
    def _assert_solar_date_time(self, dt, date, event_name, offset):
        self.assertEqual(dt.date, date)
        self.assertEqual(dt.event_name, _capitalize(event_name))
        offset = datetime.timedelta(seconds=offset)
        self.assertEqual(dt.offset, offset)


def _capitalize(s):
    return ' '.join(p.capitalize() for p in s.split())
