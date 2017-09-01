from __future__ import unicode_literals

from django.apps import AppConfig

import vesper.util.archive_lock as archive_lock


class VesperConfig(AppConfig):
    
    name = 'vesper.django.app'
    label = 'vesper'
    
    def ready(self):
        
        # Put code here to run once on startup.
        
        # Create the one and only archive lock.
        archive_lock.create_lock()
