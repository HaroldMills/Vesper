#!/usr/bin/env python

# Vesper server administration script.
# 
# This script is a simple derivative of the standard Django manage.py script.


import os
import sys

from vesper.archive_settings import archive_settings
from vesper.archive_paths import archive_paths


def main():
    
    args = sys.argv
    
    if 'createsuperuser' in args or 'runserver' in args:
        _check_archive_dir()
    
    os.environ.setdefault(
        'DJANGO_SETTINGS_MODULE', 'vesper.django.project.settings')

    from django.core.management import execute_from_command_line
    execute_from_command_line(sys.argv)
    
    
def _check_archive_dir():
    
    """
    Checks that the purported archive directory appears to contain a
    Vesper archive.
    """
    
    if archive_settings.database.engine == 'SQLite':
        
        database_file_path = archive_paths.sqlite_database_file_path
        
        if not database_file_path.exists():
            
            print((
                'The directory "{}" does not appear to be a Vesper archive '
                'directory. Please run your command again in an archive '
                'directory.').format(archive_paths.archive_dir_path))
            sys.exit(1)


if __name__ == '__main__':
    main()


# The following is the standard Django manage.py script:
# #!/usr/bin/env python
# import os
# import sys
# 
# if __name__ == "__main__":
#     os.environ.setdefault(
#         "DJANGO_SETTINGS_MODULE", "vesper.django.project.settings")
# 
#     from django.core.management import execute_from_command_line
# 
#     execute_from_command_line(sys.argv)
