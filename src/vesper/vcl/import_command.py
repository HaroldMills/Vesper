"""Module containing class `ImportCommand`."""


from vesper.vcl.delegating_command import DelegatingCommand
    

class ImportCommand(DelegatingCommand):
    
    """vcl command that imports data into an archive."""
    
    
    name = 'import'
    
    delegate_description = 'importer'
    
    delegate_extension_point_name = 'VCL Importer'
    
    help_fragment = '''
Imports data into an archive.

The importer to use and the data to import are specified by the
<importer> argument and the remaining arguments.
'''.strip()
    
    
    def execute(self):
        return self._delegate.import_()
