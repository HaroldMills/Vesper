import unittest

from nfc.util.bunch import Bunch
import nfc.archive.archive_utils as archive_utils


class ArchiveUtilsTests(unittest.TestCase):


    def test_get_clip_class_name_options(self):
        
        names = ['A', 'B', 'B.1', 'B.1.a', 'C']
        expectedResult = [
            '*', 'A', 'B', 'B*', 'B.1', 'B.1*', 'B.1.a', 'C', 'Unclassified']
        
        clip_classes = [Bunch(name=n) for n in names]
        archive = Bunch(clip_classes=clip_classes)
        
        result = archive_utils.get_clip_class_name_options(archive)
        
        self.assertEqual(result, expectedResult)
