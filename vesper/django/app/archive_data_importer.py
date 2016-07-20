import vesper.django.app.command_utils as command_utils


class ArchiveDataImporter(object):
    
    
    name = 'Archive Data Importer'
    
    
    def __init__(self, args):
        self.archive_data = command_utils.get_required_arg('archive_data', args)
    
    
    def execute(self, context):
        context.job.logger.info(self.archive_data)
        return True
