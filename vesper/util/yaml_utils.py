"""
YAML utility functions.

According to the ruamel_yaml documentation (particularly
https://yaml.readthedocs.io/en/stable/basicuse.html), the ruamel_yaml API
is "still in the process of being fleshed out" in versions 0.15+. The code
below was tested with version 0.15.46, so Vesper should pin ruamel_yaml
to that version until the API stabilizes.
"""


import ruamel.yaml as yaml
 
 
def load(source, **kwargs):
    return yaml.safe_load(source, **kwargs)
 
 
def dump(obj, dest=None, **kwargs):
     
    if dest is None:
        return yaml.safe_dump(obj, **kwargs)
     
    else:
        yaml.safe_dump(obj, dest, **kwargs)
        return None


# The following uses the `YAML` class, which is new in version 0.15 and
# may ultimately be what we want to use in this module. Note that we
# currently pass a `default_flow_style` keyword argument to the
# `yaml_utils.dump` function in a couple of places, which is not supported
# by the `dump` function below. We should either support the argument or
# not use it.
#
# from ruamel_yaml import YAML
# 
# 
# def load(source):
#     yaml = YAML()
#     return yaml.load(source)
#  
#  
# def dump(obj, dest=None):
#      
#     yaml = YAML()
#      
#     if dest is None:
#         s = io.StringIO()
#         yaml.dump(obj, s)
#         return s.getvalue()
#      
#     else:
#         yaml.dump(obj, dest)
#         return None
