"""Module containing class `ExportCommand`."""

    
from __future__ import print_function

from vesper.vcl.command import Command, CommandSyntaxError
import vesper.util.extension_manager as extension_manager


# TODO: Support export of different types of objects via subcommands,
# e.g. `export clips "MPG Ranch Clips CSV"` rather than
# `export "MPG Ranch Clips CSV"`


class ExportCommand(Command):
    
    """vcl command that exports clips from an archive."""
    
    
    name = 'export'
    
    
    @staticmethod
    def get_help(positional_args, keyword_args):
        return _get_help(positional_args, keyword_args)

    
    def __init__(self, positional_args, keyword_args):
        
        super(ExportCommand, self).__init__()
        
        # TODO: Move this check to superclass.
        if len(positional_args) != 1:
            raise CommandSyntaxError((
                '{:s} command requires exactly one positional '
                'argument.').format(self.name))
            
        exporter_class = _get_exporter_class(positional_args[0])
        self._exporter = exporter_class(positional_args[1:], keyword_args)
        
        
    def execute(self):
        return self._exporter.export()
        
        
def _get_help(positional_args, keyword_args):
    
    n = len(positional_args)
    if n == 0:
        return _get_general_help()
    else:
        return _get_specific_help(positional_args, keyword_args)
    

_HELP = '''
export <exporter> [<positional arguments>] [<keyword arguments>]

Exports data from an archive.

The data to be exported and the form in which they are exported are
specified by the <exporter> argument and the remaining arguments.

Type "vcl help export <exporter>" for help regarding a particular exporter.

Available exporters:
'''.strip()


def _get_general_help():
    
    classes = extension_manager.get_extensions('VCL Exporter')
    names = classes.keys()
    names.sort()
    names = '\n'.join(('    ' + n) for n in names)
    
    return _HELP + '\n' + names
    
    
def _get_specific_help(positional_args, keyword_args):
    
    classes = extension_manager.get_extensions('VCL Exporter')
    name = positional_args[0]
    klass = classes.get(name)
    
    if klass is None:
        return 'Unrecognized exporter "{:s}".'.format(name)
    
    else:
        help_ = klass.get_help(positional_args[1:], keyword_args)
        return ExportCommand.name + ' ' + help_


def _get_exporter_class(name):
    
    classes = extension_manager.get_extensions('VCL Exporter')
    
    try:
        return classes[name]
    except KeyError:
        raise CommandSyntaxError('Unrecognized exporter "{:s}".'.format(name))
