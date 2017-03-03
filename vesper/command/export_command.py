"""Module containing class `ExportCommand`."""


from vesper.command.command import Command, CommandSyntaxError
from vesper.singletons import extension_manager
import vesper.command.command_utils as command_utils


class ExportCommand(Command):
    
    
    extension_name = 'export'
    
    
    def __init__(self, args):
        super().__init__(args)
        exporter_spec = command_utils.get_required_arg('exporter', args)
        self._exporter = _create_exporter(exporter_spec)
        
        
    def execute(self, context):
        return self._exporter.execute(context)


def _create_exporter(exporter_spec):
    
    try:
        name = exporter_spec['name']
    except KeyError:
        raise CommandSyntaxError('Missing required exporter name.')
    
    cls = _get_exporter_class(name)

    arguments = exporter_spec.get('arguments', {})
    
    return cls(arguments)


def _get_exporter_class(name):
    classes = extension_manager.instance.get_extensions('Exporter')
    try:
        return classes[name]
    except KeyError:
        raise CommandSyntaxError(
            'Unrecognized exporter name "{}".'.format(name))
