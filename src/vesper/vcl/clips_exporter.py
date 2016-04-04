"""
Module containing class `ClipsExporter`.

A `ClipsExporter` exports clips from an archive as .wav files.
"""


import os.path

from vesper.vcl.clip_visitor import ClipVisitor
from vesper.vcl.command import CommandExecutionError
import vesper.util.os_utils as os_utils
import vesper.util.sound_utils as sound_utils
import vesper.util.text_utils as text_utils
import vesper.vcl.vcl_utils as vcl_utils


_HELP = '''
<keyword arguments>

Exports clips as .wav files to a specified directory.

See the keyword arguments documentation for how to specify the archive
from which clips are to be exported, and the subset of clips of that
archive to be exported.
'''.strip()


_ARGS = '''
- name: --output-dir
  required: true
  value description: output directory path
'''
    
    
class ClipsExporter(object):
    
    
    name = 'Clips'
    
    
    @staticmethod
    def get_help(positional_args, keyword_args):
        name = text_utils.quote_if_needed(ClipsExporter.name)
        arg_descriptors = _ClipVisitor.arg_descriptors
        args_help = vcl_utils.create_command_args_help(arg_descriptors)
        return name + ' ' + _HELP + '\n\n' + args_help

    
    def __init__(self, positional_args, keyword_args):
        super(ClipsExporter, self).__init__()
        self._clip_visitor = _ClipVisitor(positional_args, keyword_args)
        
        
    def export(self):
        return self._clip_visitor.visit_clips()
        
        
class _ClipVisitor(ClipVisitor):
    
    
    arg_descriptors = \
        vcl_utils.parse_command_args_yaml(_ARGS) + \
        ClipVisitor.arg_descriptors


    def __init__(self, positional_args, keyword_args):
        
        super(_ClipVisitor, self).__init__(positional_args, keyword_args)
        
        self._output_dir_path = vcl_utils.get_required_keyword_arg(
            'output-dir', keyword_args)
        
        
    def begin_visits(self):
        try:
            os_utils.create_directory(self._output_dir_path)
        except OSError as e:
            raise CommandExecutionError(str(e))
        
        
    def visit(self, clip):
        file_name = os.path.basename(clip.file_path)
        file_path = os.path.join(self._output_dir_path, file_name)
        sound_utils.write_sound_file(file_path, clip.sound)
