"""Module containing class `ImportCommand`."""


from vesper.vcl.command import (Command, CommandSyntaxError)
import vesper.util.extension_manager as extension_manager
    

# RESUME:
# * Refactor help functions in classify, detect, export, and import commands,
#   moving common code to extension manager where that makes sense.
# * Add example YAML file to `create` documentation.
# * Describe MPG Ranch Renamer detection handler in more detail.
# * Review present and future commands. Should `export` and `import` commands
#   have a positional argument indicating what type of object is being
#   exported or imported, or not? If not, remove TODO from `export` command.


class ImportCommand(Command):
    
    """vcl command that imports data into an archive."""
    
    
    name = 'import'
    
    
    @staticmethod
    def get_help(positional_args, keyword_args):
        return _get_help(positional_args, keyword_args)

    
    def __init__(self, positional_args, keyword_args):
        
        super(ImportCommand, self).__init__()
        
        # TODO: Move this check to superclass.
        if len(positional_args) != 1:
            raise CommandSyntaxError((
                '{:s} command requires exactly one positional '
                'argument.').format(self.name))
            
        importer_class = _get_importer_class(positional_args[0])
        self._importer = importer_class(positional_args[1:], keyword_args)
        
        
    def execute(self):
        self._importer.import_()
        
        
def _get_help(positional_args, keyword_args):

    n = len(positional_args)
    if n == 0:
        return _get_general_help()
    else:
        return _get_specific_help(positional_args, keyword_args)
    

_HELP = '''
import <importer> [<positional arguments>] [<keyword arguments>]

Imports data into an archive.

The importer to use and the data to import are specified by the
<importer> argument and the remaining arguments.

Type "vcl help import <importer>" for help regarding a particular
importer.

Available importers:
'''.strip()


def _get_general_help():
    
    classes = extension_manager.get_extensions('VCL Importer')
    names = classes.keys()
    names.sort()
    names = '\n'.join(('    ' + n) for n in names)
    
    return _HELP + '\n' + names
    
    
def _get_specific_help(positional_args, keyword_args):
    
    classes = extension_manager.get_extensions('VCL Importer')
    name = positional_args[0]
    klass = classes.get(name)
    
    if klass is None:
        return 'Unrecognized importer "{:s}".'.format(name)
    
    else:
        help_ = klass.get_help(positional_args[1:], keyword_args)
        return ImportCommand.name + ' ' + help_


def _get_importer_class(name):
    
    importer_classes = extension_manager.get_extensions('VCL Importer')
    
    try:
        return importer_classes[name]
    except KeyError:
        raise CommandSyntaxError(
            'Unrecognized importer "{:s}".'.format(name))
