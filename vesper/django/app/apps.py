from __future__ import unicode_literals

from django.apps import AppConfig


class VesperConfig(AppConfig):
    
    name = 'vesper.django.app'
    label = 'vesper'
    
    def ready(self):
        # Put code here to run once on startup.
        pass
        