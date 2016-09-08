"""Utility functions pertaining to Django."""


import os
import django
   
    
def set_up_django():
    
    """
    Sets up Django in a new process.
    
    This function should be run in a new process that will use Django
    (for example, the ORM) before the first use of Django.
    """
    
    os.environ['DJANGO_SETTINGS_MODULE'] = 'vesper.django.project.settings'
    django.setup()
