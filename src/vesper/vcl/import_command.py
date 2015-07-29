"""Module containing class `ImportCommand`."""


from vesper.vcl.delegating_command import DelegatingCommand
    

# RESUME:
# * Add example YAML file to `create` documentation.
# * Describe MPG Ranch Renamer detection handler in more detail.
# * Document decision to have `export` command not be "export clips...".
# * Make importer for YAML files currently supported by `create` command,
#   and make the `create` command simply create an empty archive.
# * Parse preferences with YAML parser rather than JSON one.
# * Add exporter that exports clips to sound files.


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
        self._delegate.import_()
