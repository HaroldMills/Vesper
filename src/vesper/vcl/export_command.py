"""Module containing class `ExportCommand`."""

    
from vesper.vcl.delegating_command import DelegatingCommand
    

class ExportCommand(DelegatingCommand):
    
    """vcl command that exports data from an archive."""
    
    
    name = 'export'
    
    delegate_description = 'exporter'
    
    delegate_extension_point_name = 'VCL Exporter'
    
    help_fragment = '''
Exports data from an archive.

The data to be exported and the form in which they are exported are
specified by the <exporter> argument and the remaining arguments.
'''.strip()
    
    
    def execute(self):
        self._delegate.export()
