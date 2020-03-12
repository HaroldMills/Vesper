"""Django management command that creates a new Vesper archive."""


from pathlib import Path
import os

from django.core.management.base import BaseCommand, CommandError

import vesper.util.os_utils as os_utils


_TEMPLATE_PATH = Path('data/createarchive/Archive Template')


class Command(BaseCommand):
    
    
    help = 'Creates a new Vesper archive'


    def add_arguments(self, parser):
        parser.add_argument('path')


    def handle(self, *args, **options):
        
        try:
            from_path = Path(__file__).parent / _TEMPLATE_PATH
            
        except Exception as e:
            raise CommandError(
                f'Could not get archive template path. '
                f'Error message was: {str(e)}')
 
        try:
            
            to_path = Path(options['path'])
            
            if not to_path.is_absolute():
                cwd = Path(os.getcwd())
                to_path = cwd / to_path
                
        except Exception as e:
            raise CommandError(
                f'Could not get new archive path. Error message was: {str(e)}')
 
        try:
            os_utils.copy_directory(from_path, to_path)
        except Exception as e:
            raise CommandError(str(e))
        
        # Create default recording directory. For some reason it doesn't
        # appear to be possible to include an empty directory in a pip
        # package!
        try:
            os_utils.create_directory(to_path / 'Recordings')
        except Exception as e:
            raise CommandError(str(e))
