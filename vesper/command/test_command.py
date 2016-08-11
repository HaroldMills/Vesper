"""Module containing class `TestCommand`."""


import time

from vesper.command.command import Command


class TestCommand(Command):
    
    
    extension_name = 'test'
    
    
    def execute(self, context):
        
        for i in range(50):
            
            time.sleep(.5)
            
            if context.stop_requested:
                return False
            
            else:
                context.job.logger.info(str(i))
                
        return True
