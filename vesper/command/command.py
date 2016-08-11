"""Module containing class `Command`."""


class CommandError(Exception):
    pass


class CommandSyntaxError(CommandError):
    pass


class CommandExecutionError(CommandError):
    pass


class Command:
    
    
    extension_name = None
    """
    The uncapitalized name of this command.
    
    The name should be a verb, for example "import" or "detect". This
    attribute should be overridden in subclasses.
    """
    
    
    def __init__(self, arguments):
        self.arguments = arguments
    
    
    @property
    def name(self):
        return self.extension_name
    
    
    def execute(self, context):
        
        """
        Executes this command in the specified context.
        
        Returns `True` if command execution completed (possibly with errors),
        or 'False` if it did not.
        """
        
        raise NotImplementedError()
