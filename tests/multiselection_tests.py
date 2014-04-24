import unittest

from nfc.ui.multiselection import Multiselection


class MultiselectionTests(unittest.TestCase):
    
    
    def test_select(self):
        self._test_cases([
            ('select', [s(10), s(20), s(15)], (((15, 15),), 15))
        ])
        
        
    def _test_cases(self, cases):
        for case in cases:
            self._test_case(*case)
            
            
    def _test_case(self, name, ops, result):
        
#        if name == 'extend after anchor resulting from toggle':
#            pass
        
        s = Multiselection(10, 20)
        
        for method_name, index in ops:
            getattr(s, method_name)(index)
                
        self._assert_selection(s, result)
        
        
    def _assert_selection(self, s, (intervals, anchor_index)):
        self.assertEqual(s.selected_intervals, tuple(intervals))
        self.assertEqual(s.anchor_index, anchor_index)
        
        
    def test_extend(self):
        
        self._test_cases([
                          
            ('extend with no anchor', [e(15)], ([(10, 15)], 10)),
            
            ('extend after anchor', [s(15), e(18)], ([(15, 18)], 15)),
            
            ('extend before anchor', [s(15), e(12)], ([(12, 15)], 15)),
            
            ('extend after and then before anchor',
             [s(15), e(18), e(12)], ([(12, 15)], 15))
                          
        ])
        
        
    def test_toggle(self):
        
        self._test_cases([
                          
            ('single toggle', [t(15)], ([(15, 15)], 15)),
            
            ('double toggle', [t(15), t(15)], ([], None)),
            
            ('detoggle of first of two singletons',
             [t(14), t(16), t(14)], ([(16, 16)], 16)),
                          
            ('detoggle of second of two singletons',
             [t(14), t(16), t(16)], ([(14, 14)], 14)),
                          
            ('toggle at beginning of selected interval',
             [s(15), e(18), t(15)], ([(16, 18)], 16)),
                          
            ('toggle at end of selected interval',
             [s(15), e(18), t(18)], ([(15, 17)], 17)),
                          
            ('toggle inside selected interval',
             [s(15), e(18), t(16)], ([(15, 15), (17, 18)], 17)),
                          
            ('toggle just before selected interval',
             [s(15), e(18), t(14)], ([(14, 18)], 14)),
                          
            ('toggle just after selected interval',
             [s(15), e(18), t(19)], ([(15, 19)], 19)),
                          
            ('toggle and extend', [t(15), e(18)], ([(15, 18)], 15)),
            
            ('two-interval toggle and extend',
             [s(10), e(12), t(15), e(18)], ([(10, 12), (15, 18)], 15)),
                          
            ('extend after anchor resulting from toggle',
             [s(15), e(18), t(16), e(19)], ([(15, 15), (17, 19)], 17)),
                          
            ('extend before anchor resulting from toggle',
             [s(15), e(18), t(16), e(14)], ([(14, 17)], 17)),
                          
            ('extend across multiple selected intervals',
             [t(13), t(15), t(19), t(17), e(12)], ([(12, 17), (19, 19)], 17)),
                          
            ('another extend across multiple selected intervals',
             [s(11), e(12), t(14), e(15), t(20), t(17), e(10)],
             ([(10, 17), (20, 20)], 17))
                          
        ])


def s(i):
    return ('select', i)


def e(i):
    return ('extend', i)


def t(i):
    return ('toggle', i)
