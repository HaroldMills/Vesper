"""Module containing class `ClassifyCommand`."""


from vesper.vcl.delegating_command import DelegatingCommand
    

class ClassifyCommand(DelegatingCommand):
    
    """vcl command that classifies clips of an archive."""
    
    
    name = 'classify'
    
    delegate_description = 'classifier'
    
    delegate_extension_point_name = 'VCL Classifier'
    
    help_fragment = '''
Classifies clips of an archive.

The classifier to use and which clips to classify are specified by the
<classifier> argument and the remaining arguments.
'''.strip()
    
    
    def execute(self):
        self._delegate.detect()
