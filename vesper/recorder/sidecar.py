from vesper.util.bunch import Bunch


class Sidecar:


    @staticmethod
    def parse_settings(settings):
        return Bunch()
    

    def __init__(self, name, settings, context):
        self._name = name
        self._settings = settings
        self._context = context


    @property
    def name(self):
        return self._name
    
    
    @property
    def settings(self):
        return self._settings
    

    @property
    def context(self):
        return self._context
    

    def start(self):
        pass

    
    def recording_will_start(self):
        pass


    def recording_did_start(self):
        pass


    def recording_will_stop(self):
        pass


    def recording_did_stop(self):
        pass


    def stop(self):
        pass


    def get_status_tables(self):
        
        """
        Gets a list of `StatusTable` objects to display for this sidecar.
        """

        raise NotImplementedError()
