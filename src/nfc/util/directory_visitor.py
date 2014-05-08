'''Module containing `DirectoryVisitor` class.'''


import os


class DirectoryVisitor(object):


    def visit(self, dir_path, level_names):
        self._visit(dir_path, level_names)
        
        
    def _visit(self, dir_path, level_names):
        
        if len(level_names) == 0:
            return
        
        start_visit, visit_file, end_visit = \
            self._get_methods(level_names[0])
        
        if start_visit is not None:
            if not start_visit(dir_path):
                return

        for _, subdir_names, file_names in os.walk(dir_path):
            
            if visit_file is not None:
                for file_name in file_names:
                    file_path = os.path.join(dir_path, file_name)
                    visit_file(file_path)
                    
            for subdir_name in subdir_names:
                subdir_path = os.path.join(dir_path, subdir_name)
                self._visit(subdir_path, level_names[1:])
                
            # stop walk from visiting subdirectories
            del subdir_names[:]
            
        if end_visit is not None:
            end_visit(dir_path)
                
                
    def _get_methods(self, level_name):
        
        method_name = '_start_{:s}_dir_visit'.format(level_name)
        start_method = getattr(self, method_name, None)
        
        method_name = '_visit_{:s}_dir_file'.format(level_name)
        file_method = getattr(self, method_name, None)
        
        method_name = '_end_{:s}_dir_visit'.format(level_name)
        end_method = getattr(self, method_name, None)
        
        return (start_method, file_method, end_method)
