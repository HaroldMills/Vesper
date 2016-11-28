import datetime

from vesper.tests.test_case import TestCase
import vesper.schedule.schedule_parser as schedule_parser


_NONRELATIVE_TIME_CASES = (
    
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


class ScheduleParserTests(TestCase):
    
    
    def test_parse_time_1(self):
        for s, args in _NONRELATIVE_TIME_CASES:
            actual = schedule_parser._parse_time(s)
            expected = datetime.time(*args)
            self.assertEqual(actual, expected)
            
            
    def test_parse_time_2(self):
        
        for event_name in _EVENT_NAMES:
            
            actual = schedule_parser._parse_time(event_name)
            self._assert_relative_time(actual, event_name, 0)
            
            for offset, seconds in _OFFSETS:
                
                for preposition, factor in _PREPOSITIONS:
                    
                    time = '{} {} {}'.format(offset, preposition, event_name)
                    actual = schedule_parser._parse_time(time)
                    
                    self._assert_relative_time(
                        actual, event_name, factor * seconds)
            
            
    def _assert_relative_time(self, rt, event_name, offset):
        self.assertEqual(rt.event_name, event_name)
        offset = datetime.timedelta(seconds=offset)
        self.assertEqual(rt.offset, offset)
            
            
    def test_parse_time_errors(self):
        for s in _BAD_TIMES:
            actual = schedule_parser._parse_time(s)
            self.assertIsNone(actual)
            
            
    def test_parse_date_time_1(self):
        for s, args in _NONRELATIVE_TIME_CASES:
            actual = schedule_parser._parse_date_time('2016-11-28 ' + s)
            expected = datetime.datetime(2016, 11, 28, *args)
            self.assertEqual(actual, expected)


    def test_parse_date_time_2(self):
        
        parse = schedule_parser._parse_date_time
        date_string = '2016-11-28'
        date = datetime.date(2016, 11, 28)
        
        for event_name in _EVENT_NAMES:
            
            actual = parse(date_string + ' ' + event_name)
            self._assert_relative_date_time(actual, date, event_name, 0)
            
            for offset, seconds in _OFFSETS:
                
                for preposition, factor in _PREPOSITIONS:
                    
                    dt = '{} {} {} {}'.format(
                        date_string, offset, preposition, event_name)
                    actual = parse(dt)
                    
                    self._assert_relative_date_time(
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
            actual = schedule_parser._parse_date_time(s)
            self.assertIsNone(actual)
            
        for s in _BAD_TIMES:
            actual = schedule_parser._parse_date_time('2016-11-28 ' + s)
            self.assertIsNone(actual)

        
    def _assert_relative_date_time(self, rdt, date, event_name, offset):
        self.assertEqual(rdt.date, date)
        self.assertEqual(rdt.event_name, event_name)
        offset = datetime.timedelta(seconds=offset)
        self.assertEqual(rdt.offset, offset)
