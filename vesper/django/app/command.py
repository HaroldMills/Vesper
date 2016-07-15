"""Module containing class `Command`."""


class Command(object):
    
    
    name = 'command'
    """
    The uncapitalized name of this command.
    
    This attribute should be overridden in subclasses.
    """
    
    
    def __init__(self, spec):
        self.spec = spec
        
        
    def execute(self, context):
        
        """
        Executes this command in the specified context.
        
        Returns `True` if command execution completed (possibly with errors),
        or 'False` if it did not.
        """
        
        raise NotImplementedError()
