import pandas as pd
import pandas.util as pd_util


import vesper.mpg_ranch.bat_utils as bat_utils

from test_case import TestCase


class BatUtilsTests(TestCase):
    
    def test_merge_kpro_and_sonobat_data(self):
        
        cases = [({
                   
            'OUT FILE': [
                'NFP-POOL_0_20130906_210212_268',    # same
                'NFP-POOL_0_20130906_212101_141',    # KPro NoID
                'NFP-POOL_0_20130906_212736_503',    # same
                'NFP-POOL_0_20130906_212752_371',    # SonoBat null
                'NFP-POOL_0_20130906_213326_001',    # different
                'NFP-POOL_0_20130906_213648_737'],   # not in SonoBat
            'AUTO ID': ['MYLU', 'NoID', 'MYYU', 'MYLU', 'MYLU', 'MYLU']
            
        }, {
                                                   
            'Filename': [
                'NFP-POOL_0_20130906_210212_268-Mylu.wav',
                'NFP-POOL_0_20130906_212101_141.wav',
                'NFP-POOL_0_20130906_212736_503.wav',
                'NFP-POOL_0_20130906_212752_371.wav',
                'NFP-POOL_0_20130906_213326_001.wav',
                'NFP-POOL_0_20130906_213651_581.wav'],    # not in KPro
            'Consensus': ['Mylu', 'Mylu', 'Myyu', '', 'bobo', 'Mylu']
            
        }, {
                                                     
            'file_name_base': [
                'NFP-POOL_0_20130906_210212_268',
                'NFP-POOL_0_20130906_212736_503'],
            'species': ['MYLU', 'MYYU']
                  
        })]
        
        for kpro, sonobat, expected in cases:
            kpro = pd.DataFrame(kpro)
            sonobat = pd.DataFrame(sonobat)
            expected = pd.DataFrame(expected)
            result = bat_utils.merge_kpro_and_sonobat_data(kpro, sonobat)
            pd_util.testing.assert_frame_equal(
                result, expected, check_names=True)
