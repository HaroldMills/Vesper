"""
Module containing the Vesper plugin manager.

The module contains both the `PluginManager` class, and the singleton
instance `plugin_manager` of that class. The plugin manager is created
when this module is imported, and should be accessed by other modules
via the `plugin_manager` module attribute, e.g.:

    from vesper.plugin.plugin_manager import plugin_manager
"""


from vesper.plugin.root_plugin_type import RootPluginType
from vesper.util.lazily_initialized import LazilyInitialized


'''
The following are working notes concerning the design of the plugin manager
and other plugin classes. Some of the notes mention ideas that have been
rejected. The notes can be deleted when the design of the classes has
stabilized.

There are *plugins*, *plugin types*, and *plugin type API versions*.
Plugin types are themselves plugins, allowing third-party Vesper packages
to define their own plugin types. There is exactly one built-in plugin,
the *root plugin type*, which is the plugin type of plugin types. It is
its own type. When the plugin manager initializes, it creates the root
plugin type and uses it to load the other plugin types. All other plugins
are loaded only upon request, by their types.

Plugin types perform the following functions:

* Document the supported plugin types and API versions of a particular
  Vesper installation.
  
* Load and validate plugins of their type.

Choose one of two options:

* Single instance of plugin class is factory that creates objects that
  detect, classify, etc.
  
* Plugin class itself is factory, instances of which detect, classify, etc.

Can we represent plugin type API versions as abstract classes that can
be (but do not have to be) subclassed by implementations? Does this work
with both of the above options? Such API version classes would not
themselves be plugins: they would just be convenient but optional plugin
superclasses, providing partial implementations and implementation
guidance.

Does it really make sense to distinguish between plugin types and plugin
API versions? I suspect so: the plugin type / API version hierarchical
structure is real, and we will probably want the plugin manager UI to
reflect it. How exactly does code that uses plugins work with plugins
of different API versions?

2020-09-23
----------

This is getting too complicated, and difficult to think about. I need
to design and implement something relatively simple and get some
experience using it before worrying about possible features like plugin
API versions that we might not really need.

With this in mind, here are some working design decisions:

* A *plugin* is a Python class with certain class attributes that
provide information about the plugin. In most cases, for example
for detector and classifier plugins, Vesper uses a plugin by creating
an instance of it and calling methods on the instance. However, some
plugins may just provide information via class attributes and never
be instantiated. See the next point for an example of this.

* Each plugin is of one of a set of *plugin types*. A plugin type is
itself a plugin, i.e. it is a Python class with certain attributes.
Vesper discovers the available plugin types via the `vesper.plugin_types`
entry point group. Vesper never instantiates plugin types: it only reads
their class attributes.

* The plugin manager loads plugin types during initialization. Other
plugins are loaded lazily, though all of the plugins of a particular
type are loaded at the same time.

* I will forget about plugin API versions initially: each new API
will require a new plugin type.

2020-09-29
----------
What are semantics of plugin versioning?

Things related to a plugin that have versions:

* Plugin API (of plugin type) that plugin implements
* Plugin software
* Python package containing plugin

Example of a detector plugin class:

class OldBirdTseepDetectorRedux_1_1_0:
    
    name = 'Old Bird Tseep Detector Redux'
    version = '1.1.0'
    description = 'Python reimplementation of Old Bird Tseep Detector.'
    author = 'Harold Mills'
    license = 'MIT'
    plugin_type_name = 'Detector'
    implemented_api_version = '1.0'
'''
    
    
class PluginManager(LazilyInitialized):
    
    """
    Plugin manager, which discovers, loads, and provides access to plugins.
    """
    
    
    def _init(self):
        self._root_plugin_type = RootPluginType()
        plugin_types = self._root_plugin_type.get_plugins()
        self._plugin_types = dict((t.name, t) for t in plugin_types)
               
        
    @LazilyInitialized.initter
    def get_plugin_type(self, type_name):
        return self._root_plugin_type.get_plugin(type_name)
        
        
    @LazilyInitialized.initter
    def get_plugins(self, type_name):
        plugin_type = self.get_plugin_type(type_name)
        return plugin_type.get_plugins()
        
        
    @LazilyInitialized.initter
    def get_plugin(self, type_name, plugin_name):
        plugin_type = self.get_plugin_type(type_name)
        return plugin_type.get_plugin(plugin_name)


plugin_manager = PluginManager()
