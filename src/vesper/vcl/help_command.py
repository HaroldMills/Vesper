"""Module containing class `HelpCommand`."""


from __future__ import print_function

from vesper.vcl.command import Command
import vesper.util.extension_manager as extension_manager


_HELP = '''
[<command> [<arguments>]]

Displays help for one or all commands.

If <command> is not specified, brief help is displayed for all commands.
If <command> is specified, more detailed help is displayed for just that
command. For some commands, additional command arguments can be specified
as <arguments> to obtain even more detailed help.
'''.strip()


class HelpCommand(Command):
    
    """VCL command that displays help text."""
    
    
    name = 'help'
    
    
    @staticmethod
    def get_help(positional_args, keyword_args):
        return HelpCommand.name + ' ' + _HELP

    
    def __init__(self, positional_args, keyword_args):
        super(HelpCommand, self).__init__()
        self._positional_args = list(positional_args)
        self._keyword_args = dict(keyword_args)
        
        
    def execute(self):
        help_ = _get_help(self._positional_args, self._keyword_args)
        print('\n' + help_ + '\n')
        return True
        
        
_GENERAL_HELP = '''
help: Display vcl help.

Usage: help [<command>]

If a command is specified, detailed help is displayed for that command only.
If no command is specified more general help is displayed for all commands.
'''.strip()
    
    
def _get_help(positional_args, keyword_args):
    n = len(positional_args)
    if n == 0:
        return _get_general_help()
    else:
        return _get_specific_help(positional_args, keyword_args)


_GENERAL_HELP_PREFIX = '''
Usage: vcl <command> [<positional arguments>] [<keyword arguments>]

Type "vcl help <command> [<arguments>]" for help regarding a particular
command.

Available commands:
'''.strip()


def _get_general_help():
    
    command_classes = extension_manager.get_extensions('VCL Command')
    command_names = command_classes.keys()
    command_names.sort()
    command_names = '\n'.join(('    ' + n) for n in command_names)
    
    return _GENERAL_HELP_PREFIX + '\n' + command_names
    
    
def _get_specific_help(positional_args, keyword_args):
    
    command_classes = extension_manager.get_extensions('VCL Command')
    command_name = positional_args[0]
    command_class = command_classes.get(command_name)
    
    if command_class is None:
        return 'Unrecognized command "{:s}".'.format(command_name)
    
    else:
        try:
            help_ = command_class.get_help(positional_args[1:], keyword_args)
        except AttributeError:
            return 'Could not find help for command "{:s}".'.format(
                command_name)
        else:
            return 'Usage: vcl ' + help_
