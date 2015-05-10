"""Module containing class `ImportCommand`."""


from mpg_ranch.importer import Importer as MpgRanchImporter
from vesper.vcl.command import (
    Command, CommandSyntaxError, CommandExecutionError)
import vesper.vcl.vcl_utils as vcl_utils


# TODO: Get importer names from importer classes.
_IMPORTER_CLASSES = {
    'MPG Ranch': MpgRanchImporter
}


class ImportCommand(Command):
    
    """vcl command that imports data into an archive."""
    
    
    name = 'import'
    
    
    @staticmethod
    def get_help_text():
        # TODO: Get help text for individual importers from the importers.
        return 'import "MPG Ranch" <data dir>'
    
    
    def __init__(self, positional_args, keyword_args):
        
        super(ImportCommand, self).__init__()
        
        # TODO: Move this check to superclass.
        if len(positional_args) != 2:
            raise CommandSyntaxError((
                '{:s} command requires exactly two positional '
                'arguments.').format(self.name))
            
        # TODO: Have importer parse source dir path, and make it a
        # keyword argument rather than a positional argument.
        importer_name, self._source_dir_path = positional_args
        
        klass = _get_importer_class(importer_name)
        self._importer = klass(positional_args[2:], keyword_args)
        
        self._archive_dir_path = vcl_utils.get_archive_dir_path(keyword_args)
        
        
    def execute(self):
        
        # TODO: In the end, this method should simply invoke the
        # importer's `import_` method.
        
        vcl_utils.check_dir_path(self._source_dir_path)
    
        archive = vcl_utils.open_archive(self._archive_dir_path)
    
        try:
            success = self._importer.import_(self._source_dir_path, archive)
        except Exception as e:
            raise CommandExecutionError(str(e))
        finally:
            archive.close()
        
        # TODO: Move this into importer `import_` method?
        self._importer.log_summary()
        
        return success
        

def _get_importer_class(name):

    try:
        return _IMPORTER_CLASSES[name]
    except KeyError:
        raise CommandSyntaxError(
           'Unrecognized importer "{:s}".'.format(name))
