"""Module containing class `ExportCommand`."""

    
from __future__ import print_function

from mpg_ranch.clips_csv_exporter \
    import ClipsCsvExporter as MpgRanchClipsCsvExporter
from vesper.vcl.command import Command, CommandSyntaxError


_EXPORTER_CLASSES = {
    'MPG Ranch Clips CSV': MpgRanchClipsCsvExporter
}


class ExportCommand(Command):
    
    """vcl command that exports clips from an archive."""
    
    
    name = 'export'
    
    
    @staticmethod
    def get_help_text():
        # TODO: Get help text for individual exporters from the exporters.
        return (
            'export "MPG Ranch Clips CSV" '
            '[--output-file <file path>] '
            '[--station <station name>] [--stations <station names>] '
            '[--detector <detector name>] [--detectors <detector names>] '
            '[--clip-class <clip class name>] '
            '[--clip-classes <clip class names>] '
            '[--date <YYYY-MM-DD>] '
            '[--start-date <YYYY-MM-DD] [--end-date <YYYY-MM-DD>] '
            '[--archive <archive dir>]')

    
    def __init__(self, positional_args, keyword_args):
        
        super(ExportCommand, self).__init__()
        
        # TODO: Move this check to superclass.
        if len(positional_args) != 1:
            raise CommandSyntaxError((
                '{:s} command requires exactly one positional '
                'argument.').format(self.name))
            
        klass = _get_exporter_class(positional_args[0])
        self._exporter = klass(positional_args[1:], keyword_args)
        
        
    def execute(self):
        return self._exporter.export()
        
        
def _get_exporter_class(name):
    try:
        return _EXPORTER_CLASSES[name]
    except KeyError:
        raise CommandSyntaxError(
            'Unrecognized export type "{:s}".'.format(name))
