"""
Module containing class `CallNoiseClassifier`.

A `CallNoiseClassifier` assigns clips to the `'Call'` and `'Noise'` classes.
Each clip is assigned to one of those to classes.
"""


from __future__ import print_function

from vesper.vcl.clip_visitor import ClipVisitor
import vesper.util.text_utils as text_utils
import vesper.vcl.vcl_utils as vcl_utils


_HELP = '''
<keyword arguments>

Classifies clips as either "Call" clips or "Noise" clips.

Each clip is assigned to either the "Call" class or the "Noise" class.

See the keyword arguments documentation for how to specify the archive
in which clips are to be classified, and the subset of clips of that
archive to be classified.
'''.strip()


_ARG_DESCRIPTORS = \
    vcl_utils.ARCHIVE_ARG_DESCRIPTORS + \
    vcl_utils.CLIP_QUERY_ARG_DESCRIPTORS
    
    
class CallNoiseClassifier(object):
    
    
    name = 'Call/Noise Classifier'
    
    
    @staticmethod
    def get_help(positional_args, keyword_args):
        name = text_utils.quote_if_needed(CallNoiseClassifier.name)
        arg_descriptors = _ClipVisitor.arg_descriptors
        args_help = vcl_utils.create_command_args_help(arg_descriptors)
        return name + ' ' + _HELP + '\n\n' + args_help

    
    def __init__(self, positional_args, keyword_args):
        super(CallNoiseClassifier, self).__init__()
        self._clip_visitor = _ClipVisitor(positional_args, keyword_args)
        
        
    def classify(self):
        return self._clip_visitor.visit_clips()
        
        
class _ClipVisitor(ClipVisitor):
    
    
    def visit(self, clip):
        clip.clip_class_name = _classify_clip(clip)
        
        
def _classify_clip(clip):
    return 'Noise'
