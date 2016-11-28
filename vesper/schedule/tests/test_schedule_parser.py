import datetime

from vesper.tests.test_case import TestCase
import vesper.schedule.schedule_parser as schedule_parser


_EVENT_NAMES = (
    'sunrise', 'sunset', 'civil dawn', 'civil dusk', 'nautical dawn',
    'nautical dusk', 'astronomical dawn', 'astronomical dusk')


class ScheduleParserTests(TestCase):
    
    
    def test_parse_time_errors(self):
        
        cases = (
            
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
        
        for s in cases:
            self._assert_raises(ValueError, schedule_parser._parse_time, s)
            
            
    def test_parse_time_1(self):
        
        cases = (
            
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
            ('midnight', (0,)),
            
        )
        
        for s, args in cases:
            actual = schedule_parser._parse_time(s)
            expected = datetime.time(*args)
            self.assertEqual(actual, expected)
            
            
    def test_parse_time_2(self):
        
        offsets = (
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
        
        prepositions = (
            ('before', -1),
            ('after', 1)
        )
        
        for event_name in _EVENT_NAMES:
            
            actual = schedule_parser._parse_time(event_name)
            self._assert_relative_time(actual, event_name, 0)
            
            for offset, seconds in offsets:
                
                for preposition, factor in prepositions:
                    
                    time = '{} {} {}'.format(offset, preposition, event_name)
                    actual = schedule_parser._parse_time(time)
                    
                    self._assert_relative_time(
                        actual, event_name, factor * seconds)
            
            
    def _assert_relative_time(self, rt, event_name, offset):
        self.assertEqual(rt.event_name, event_name)
        offset = datetime.timedelta(seconds=offset)
        self.assertEqual(rt.offset, offset)
