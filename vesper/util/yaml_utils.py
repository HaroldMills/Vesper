"""YAML utility functions."""


from io import StringIO

from ruamel.yaml import YAML


def load(source):
    yaml = _create_yaml()
    return yaml.load(source)
 

def _create_yaml():

    # We use the default 'rt' type, which is safe. We also use the
    # pure-Python implementation, which is slower than the default
    # C implementation but less quirky. See
    # https://yaml.readthedocs.io/en/latest for details.
     return YAML(pure=True)


def dump(obj, dest=None, default_flow_style=True):
    
    yaml = _create_yaml()

    if not default_flow_style:
        yaml.default_flow_style=False
     
    if dest is None:
        s = StringIO()
        yaml.dump(obj, s)
        return s.getvalue()
     
    else:
        yaml.dump(obj, dest)
        return None
