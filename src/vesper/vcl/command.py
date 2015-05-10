"""Module containing class `Command`."""


class CommandError(Exception):
    pass


class CommandSyntaxError(CommandError):
    pass


class CommandExecutionError(CommandError):
    pass


class Command(object):
    
    """
    Abstract superclass of vcl commands.
    
    The `__init__` method of a subclass should be of the form:
    
         def __init__(self, positional_args, keyword_args):
             ...
             
    The `__init__` method should check the syntax of the command and
    raise a `CommandSyntaxError` if a syntax error is detected.
    """
    
    
    name = None
    """the name of this command."""
    
    
    def execute(self):
        
        """
        Executes this command.
        
        :Returns:
            `True` if and only if no errors occurred during command execution.
            
            If this method returns `False`, errors occurred but they were
            not fatal. When a fatal error occurs the method raises a
            `CommandExecutionError` exception.
            
        :Raises CommandExecutionError:
            if a fatal error occurs during command execution.
        """
        
        raise NotImplementedError()
