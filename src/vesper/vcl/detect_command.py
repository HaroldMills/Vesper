"""Module containing class `DetectCommand`."""


from vesper.vcl.delegating_command import DelegatingCommand
    

class DetectCommand(DelegatingCommand):
    
    """vcl command that runs a detector on one or more inputs."""
    
    
    name = 'detect'
    
    delegate_description = 'detector'
    
    delegate_extension_point_name = 'VCL Detector'
    
    help_fragment = '''
Runs a detector on one or more inputs.

The detector to use and its configuration are specified by the
<detector> argument and the remaining arguments.
'''.strip()
    
    
    def execute(self):
        self._delegate.detect()
