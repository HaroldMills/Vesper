"""Module containing class `MetadataImporter`."""


import logging

import vesper.command.command_utils as command_utils
import vesper.django.app.metadata_import_utils as metadata_import_utils


class MetadataImporter:
    
    """
    Importer for metadata including stations, devices, etc.
    
    The data to be archived are in the `metadata` command argument.
    The value of the argument is a mapping from string keys like `'stations'`
    and `'devices'` to collections of mappings, with each mapping in the
    collection describing the fields of one archive object.
    """
    
    
    extension_name = 'Metadata Importer'
    
    
    def __init__(self, args):
        self.metadata = command_utils.get_required_arg('metadata', args)
    
    
    def execute(self, job_info):
        
        self._logger = logging.getLogger()
        
        try:
            metadata_import_utils.import_metadata(
                self.metadata, self._logger, job_info.job_id)
                
        except Exception:
            self._logger.error(
                'Metadata import failed with an exception. Database '
                'has been restored to its state before the import. See '
                'below for exception traceback.')
            raise
        
        return True
