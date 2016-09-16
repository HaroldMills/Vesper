#!/usr/bin/env python

# Vesper server administration script.
# 
# This script is a simple derivative of the standard Django manage.py script.


import os
import sys

import vesper.django.project.settings as settings


def main():
    
    args = sys.argv
    
    if 'createsuperuser' in args or 'runserver' in args:
        _check_cwd()
    
    os.environ.setdefault(
        'DJANGO_SETTINGS_MODULE', 'vesper.django.project.settings')

    from django.core.management import execute_from_command_line
    execute_from_command_line(sys.argv)
    
    
def _check_cwd():
    
    """
    Checks that the current working directory is a Vesper archive directory.
    """
    
    current_dir_path = os.getcwd()
    database_file_path = os.path.join(
        current_dir_path, settings.VESPER_ARCHIVE_DATABASE_FILE_NAME)
    if not os.path.exists(database_file_path):
        print((
            'The current directory "{}" does not appear to be a Vesper '
            'archive directory. Please run your command again an archive '
            'directory.').format(current_dir_path))
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
