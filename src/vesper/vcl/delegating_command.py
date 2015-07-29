"""Module containing class `DelegatingCommand`."""


from vesper.vcl.command import (Command, CommandSyntaxError)
import vesper.util.extension_manager as extension_manager
import vesper.vcl.vcl_utils as vcl_utils


_GENERAL_DELEGATE_HELP = '''
Type "vcl help {:s}" for help regarding a particular
{:s}.

Available {:s}:
'''.strip()


class DelegatingCommand(Command):
    
    """
    Superclass of commands that execute by means of a delegate.
    
    Any number of different types of delegates may be available for a
    single command. The delegates types are included in a system as
    extensions.
    """
    
    
    delegate_description = None
    '''
    A word describing a delegate for this command, for example "classifier".
    '''
    
    delegate_description_plural = None
    '''
    Plural form of `delegate_description`, or `None` if the plural is
    formed from `delegate_description` by simply appending an `s`.
    '''
    
    delegate_extension_point_name = None
    '''
    The name of the delegate extension point, for example "VCL Classifier".
    '''
    
    help_fragment = None
    '''
    Help fragment, inserted between example invocation and explanation
    of how to obtain help for specific command delegates.
    '''


    @classmethod
    def get_help(cls, positional_args, keyword_args):
        n = len(positional_args)
        if n == 0:
            return cls._get_general_help()
        else:
            return cls._get_specific_help(positional_args, keyword_args)

    
    @classmethod
    def _get_general_help(cls):
        
        prefix = cls._get_general_help_prefix()
        
        classes = extension_manager.get_extensions(
            cls.delegate_extension_point_name)
        
        names = classes.keys()
        
        if len(names) == 0:
            names = '    None.'
        
        else:
            names.sort()
            names = '\n'.join(('    ' + n) for n in names)
        
        return prefix + '\n' + names
        
        
    @classmethod
    def _get_general_help_prefix(cls):
        
        command_prefix = '{:s} <{:s}>'.format(
            cls.name, cls.delegate_description)
        
        prefix = \
            command_prefix + ' [<positional arguments>] [<keyword arguments>]'
            
        suffix = _GENERAL_DELEGATE_HELP.format(
            command_prefix, cls.delegate_description,
            cls._get_delegate_description_plural())
        
        return prefix + '\n\n' + cls.help_fragment + '\n\n' + suffix
        

    @classmethod
    def _get_delegate_description_plural(cls):
        plural = cls.delegate_description_plural
        if plural is None:
            plural = cls.delegate_description + 's'
        return plural
    
    
    @classmethod
    def _get_specific_help(cls, positional_args, keyword_args):
        
        try:
            extension = vcl_utils.get_command_delegate_extension(
                positional_args[0], cls.delegate_extension_point_name,
                cls.delegate_description)
            
        except CommandSyntaxError as e:
            return str(e)
        
        else:
            help_ = extension.get_help(positional_args[1:], keyword_args)
            return cls.name + ' ' + help_


    def __init__(self, positional_args, keyword_args):
        
        super(DelegatingCommand, self).__init__()
        
        # TODO: Move this check to superclass.
        if len(positional_args) != 1:
            raise CommandSyntaxError((
                '{:s} command requires exactly one positional '
                'argument.').format(self.name))
            
        extension = vcl_utils.get_command_delegate_extension(
            positional_args[0], self.delegate_extension_point_name,
            self.delegate_name)

        self._delegate = extension(positional_args[1:], keyword_args)
