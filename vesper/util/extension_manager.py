"""Provides access to the extensions of a program."""


# TODO: Use a hierarchical name space for extensions?


# TODO: Don't hard-code extensions. They should specified from outside
# somehow. One possibility is that they could be specified in plug-in
# manifest files. It would also be desirable to be able to specify
# different subsets of installed extensions to work with at different
# times, say for different analysis projects.


_extensions = None


def get_extensions(extension_point_name):
    _initialize_if_needed()
    extensions = _extensions.get(extension_point_name, ())
    return dict((e.name, e) for e in extensions)
    
    
def _initialize_if_needed():
    if _extensions is None:
        load_extensions()
        
        
def load_extensions():
    
    # These imports are here rather than at top level to avoid circular
    # import problems.
    from vesper.django.app.archive_data_importer import ArchiveDataImporter
    from vesper.django.app.import_command import ImportCommand
    from vesper.django.app.test_command import TestCommand

    global _extensions
    
    _extensions = {
                               
        'Vesper Command': (
            ImportCommand,
            TestCommand,
        ),
                   
        'Importer': (
            ArchiveDataImporter,
        )
            
    }
