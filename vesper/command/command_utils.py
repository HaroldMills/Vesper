from vesper.command.command import CommandSyntaxError


# TODO: Add type checking.


def get_required_arg(name, args):
    try:
        return args[name]
    except KeyError:
        raise CommandSyntaxError(
            'Missing required command argument "{}".'.format(name))


def get_optional_arg(name, args, default=None):
    return args.get(name, default)
