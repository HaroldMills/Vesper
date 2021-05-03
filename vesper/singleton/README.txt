Notes on the design of Vesper's singleton classes
-------------------------------------------------

Vesper uses several singleton classes, i.e. classes of which only one
instance is created to serve a process of the Vesper server. These
include the extension manager, the preference manager, the preset
manager, and others.

Each Vesper singleton class is defined in its own module, most of
which are in the `vesper.util` package. For example, the
`ExtensionManager` class is defined in the
`vesper.util.extension_manager` module. Each singleton instance
lives in its own, separate module in the `vesper.singleton`
package. For example, the extension manager instance is the
`extension_manager` attribute of the
`vesper.singleton.extension_manager` module.

Vesper's singleton instances could live in the modules that define
their classes rather than in their own, separate modules. For
example, we could put both the `Extension Manager` class and the
`extension_manager` instance of that class in the
`vesper.util.extension_manager` module. However, that can (and did,
when I tried it) complicate unit testing of the classes by adding
unnecessary dependencies to the modules that define them. It's better
to keep the concern of defining a class separate from the concern of
creating Vesper's particular singleton instance of that class.

At one point all of Vesper's singleton instances were in a single
`vesper.util.singletons` module. The current design better separates
the concerns of the different singletons. For example, it allows you
to use one singleton instance without requiring the creation (by
importing the `vesper.util.singletons` module) of all of the
singleton instances.

Some people recommend implementing singletons as Python modules
(which are, after all, singletons) rather than class instances. I
chose not to do that, however, since I wanted to write unit tests for
the singletons, and it seemed easier to write unit tests for Python
classes than it is for Python modules. During unit testing, the
classes are typically not used as singletons, since it is useful to
create separate instance of them for separate tests. It is only during
normal Vesper operation that the classes function as singletons.
