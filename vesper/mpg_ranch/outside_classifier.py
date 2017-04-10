import logging


_logger = logging.getLogger()


class OutsideClassifier:
    
    
    extension_name = 'MPG Ranch Outside 1.0'
    
    
    def classify(self, clip):
        _logger.info('OutsideClassifier.classify', str(clip))
        return True
    