"""Module containing class `Visitor`."""


import vesper.vcl.vcl_utils as vcl_utils


class Visitor(object):
    
    """
    Abstract archive object visitor superclass.
    
    A *visitor* visits each object of a set of objects from an archive,
    performing some operation on the object.
    """
    
    
    arg_descriptors = vcl_utils.ARCHIVE_ARG_DESCRIPTORS


    def __init__(self, positional_args, keyword_args):
        super(Visitor, self).__init__()
        self._archive_dir_path = vcl_utils.get_archive_dir_path(keyword_args)
                
    
    def objects(self):
        """Generator that yields the objects to be visited."""
        raise NotImplementedError()
    
    
    def visit_objects(self):
        
        self._success = True
        
        self._archive = vcl_utils.open_archive(self._archive_dir_path)
        
        self.begin_visits()
        
        for obj in self.objects():
            self.visit(obj)
            
        self.end_visits()
        
        self._archive.close()
        
        return self._success
    
    
    def begin_visits(self):
        pass
    
    
    def visit(self, obj):
        pass
    
    
    def end_visits(self):
        pass
