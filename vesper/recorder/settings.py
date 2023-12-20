from collections.abc import Mapping

import vesper.util.yaml_utils as yaml_utils


class Settings:


    @staticmethod
    def create_from_yaml_file(file_path):
        with open(file_path) as file:
            mapping = yaml_utils.load(file)
        return Settings(mapping)


    def __init__(self, mapping):
        self._mapping = mapping


    def get(self, path, default=None):
        
        s = self._mapping

        for name in path.split('.'):

            if isinstance(s, Mapping) and name in s:
                s = s[name]
            else:
                return default
            
        # If we get here, the setting is present with value `s`.
        return s
    

    def get_required(self, path):

        s = self._mapping

        for name in path.split('.'):

            if isinstance(s, Mapping) and name in s:
                s = s[name]
            else:
                raise KeyError(f'Required setting "{path}" is missing.')
            
        # If we get here, the setting is present with value 's'.
        return s
