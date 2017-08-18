from unittest import TestCase

from vesper.old_bird.old_bird_detector_redux_1_1 import _TransientFinder


_MIN_LENGTH = 100
_MAX_LENGTH = 400
_FINAL_FALL = (1000000, False)


class TransientFinderTests(TestCase):


    def test(self):
        
        cases = [
            
            # no transitions, no transients
            ([], []),
            
            # falls only, no transients
            ([(1000, False)], []),
            ([(1000, False), (1100, False)], []),
             
            # one transient, length less than minimum
            ([(1000, True), (1001, False)], [(1000, 100)]),
            ([(1000, True), (1050, False)], [(1000, 100)]),
            ([(1000, True), (1099, False)], [(1000, 100)]),
             
            # one transient, minimum length
            ([(1000, True), (1100, False)], [(1000, 100)]),
             
            # one transient, length between minimum and maximum
            ([(1000, True), (1200, False)], [(1000, 200)]),
              
            # one transient, maximum length
            ([(1000, True), (1400, False)], [(1000, 400)]),
              
            # one transient, length greater than maximum
            ([(1000, True), (1401, False)], [(1000, 400)]),
            ([(1000, True), (1500, False)], [(1000, 400)]),
            
            # two transients
            ([(1000, True), (1200, False), (1400, True), (1600, False)],
             [(1000, 200), (1400, 200)]),
                  
            # two closely spaced transients
            ([(1000, True), (1200, False), (1201, True), (1401, False)],
             [(1000, 200), (1201, 200)]),
                  
            # one transient preceded by fall
            ([(500, False), (1000, True), (1200, False)], [(1000, 200)]),
             
            # two consecutive rises separated by less than maximum length
            ([(1000, True), (1100, True), (1200, False)], [(1000, 200)]),
            ([(1000, True), (1399, True)], [(1000, 400)]),
            
            # two consecutive rises separated by exactly maximum length
            # (the second rise is ignored)
            ([(1000, True), (1400, True)], [(1000, 400)]),
            
            # two consecutive rises separated by more than maximum length
            ([(1000, True), (1401, True)], [(1000, 400), (1401, 400)]),
            ([(1000, True), (2000, True), (3000, False)],
             [(1000, 400), (2000, 400)]),
                 
            # rise after transient of less than minimum length, not more
            # than one sample past end of minimum length transient
            ([(1000, True), (1010, False), (1020, True)], [(1000, 400)]),
            ([(1000, True), (1010, False), (1099, True)], [(1000, 400)]),
            ([(1000, True), (1010, False), (1100, True)], [(1000, 400)]),
            
            # rise after transient of less than minimum length, more than
            # one sample past end of minimum length transient
            ([(1000, True), (1010, False), (1101, True)],
             [(1000, 100), (1101, 400)]),
                 
            # fall after transient of less than minimum length, before
            # end of minimum length transient
            ([(1000, True), (1010, False), (1020, False)], [(1000, 100)]),
            
        ]
        
        for crossings, expected_clips in cases:
            
            # Pass case crossings all at once.
            finder = _TransientFinder(_MIN_LENGTH, _MAX_LENGTH)
            clips = finder.process(crossings)
            clips += finder.complete_processing([_FINAL_FALL])
            self.assertEqual(clips, expected_clips)
                      
            # Pass case crossings one at a time.
            finder = _TransientFinder(_MIN_LENGTH, _MAX_LENGTH)
            clips = []
            for crossing in crossings:
                clips += finder.process([crossing])
            clips += finder.complete_processing([_FINAL_FALL])
            self.assertEqual(clips, expected_clips)
