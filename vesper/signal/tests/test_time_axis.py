from vesper.signal.increasing_linear_map import IncreasingLinearMap
from vesper.signal.time_axis import TimeAxis
from vesper.tests.test_case import TestCase
import vesper.signal.tests.utils as utils


class TimeAxisTests(TestCase):


    def test_init(self):
                 
        cases = [
            (0, 24000),
            (1, 32000),
            (10, 48000),
            (10, 48000, 1)
        ]
         
        for case in cases:
            a = TimeAxis(*case)
            self._assert_axis(a, *case)
            
            
    def _assert_axis(self, a, length, frame_rate, start_time=0):
        
        frame_period = 1 / frame_rate
        
        self.assertEqual(a.length, length)
        self.assertEqual(a.frame_rate, frame_rate)
        self.assertEqual(a.frame_period, frame_period)
        self.assertEqual(a.sample_rate, frame_rate)
        self.assertEqual(a.sample_period, frame_period)
        
        index_to_time = IncreasingLinearMap(frame_period, start_time)

        start_time = index_to_time(0) if length != 0 else None
        self.assertEqual(a.start_time, start_time)
        
        end_time = index_to_time(a.length - 1) if length != 0 else None
        self.assertEqual(a.end_time, end_time)
        
        span = end_time - start_time if length != 0 else None
        self.assertEqual(a.span, span)
        
        duration = span + frame_period if length != 0 else 0
        self.assertEqual(a.duration, duration)
                    

    def test_initializer_errors(self):
        
        cases = [
            (-1, 24000),
            (0, 0)
        ]
        
        for case in cases:
            self.assert_raises(ValueError, TimeAxis, *case)
        
        
    def test_eq(self):
        args = (10, 2)
        changes = (11, 3)
        utils.test_eq(TimeAxis, args, changes)
        
        
#     def test_index_to_time_mapping(self):
#           
#         a = TimeAxis(5, 10, 2, IncreasingLinearMap(.5, .25))
#            
#         cases = [
#             (10, 5.25),
#             (np.array([]), np.array([])),
#             (np.array([10, 11]), np.array([5.25, 5.75]))
#         ]
#            
#         utils.test_mapping(a, 'index_to_time', 'time_to_index', cases)
#   
#       
#     def test_index_to_datetime_mapping(self):
#   
#         dt = datetime.datetime
#           
#         reference = Bunch(index=5, datetime=dt(2016, 4, 29, 1, 2, 3))
#         a = TimeAxis(5, 10, 2, None, reference)
#            
#         cases = [
#             (10, dt(2016, 4, 29, 1, 2, 5, 500000)),
#             (np.array([]), []),
#             (np.array([9, 11]), np.array(
#                 [dt(2016, 4, 29, 1, 2, 5), dt(2016, 4, 29, 1, 2, 6)]))
#         ]
#            
#         utils.test_mapping(
#             a, 'index_to_datetime', 'datetime_to_index', cases)
