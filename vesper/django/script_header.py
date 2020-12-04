"""
Header module for Vesper scripts that use Django.

A script that uses Django (for example, the Django ORM) can import this
module to set up Django. The script should import this module before
doing anything else concerning Django, such as importing data model
classes. For example, the script can have as its first non-comment,
non-whitespace line:

    import vesper.django.script_header as script_header
    
Note that the import is executed only for the side effect of setting
up Django, and not to actually do anything with the imported module.
"""


import os

# Set up Django.
os.environ['DJANGO_SETTINGS_MODULE'] = 'vesper.django.project.settings'
import django
django.setup()
