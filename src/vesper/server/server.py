import os.path

from tornado.ioloop import IOLoop
from tornado.web import Application, RequestHandler


_PORT_NUM = 8888
_TEMPLATES_DIR_NAME = 'templates'
_STATIC_DIR_NAME = 'static'
_SOUNDS_DIR_NAME = 'sounds'
_SOUND_FILE_NAME_EXTENSION = '.wav'


class Server(object):
    
    def run(self):
        app = _create_app()
        app.listen(_PORT_NUM)
        IOLoop.current().start()
        
        
def _create_app():
    
    sounds_dir_path = _get_path(_SOUNDS_DIR_NAME)
    
    kwargs = {'sounds_dir_path': sounds_dir_path}
    
    handlers = [
        (r'/', _MainHandler),
        (r'/demo/recording', _RecordingDemoHandler, kwargs),
        (r'/demo/recording/new', _RecordingDemoNewHandler, kwargs),
        (r'/sounds', _SoundsHandler, kwargs),
        (r'/sounds/(.+)', _SoundHandler, kwargs),
        (r'/sound_files/(.+)', _SoundFileHandler, kwargs)
    ]
    
    template_path = _get_path(_TEMPLATES_DIR_NAME)
    
    static_path = _get_path(_STATIC_DIR_NAME)
    
    return Application(
        handlers, template_path=template_path, static_path=static_path)

    
def _get_path(*args):
    module_dir_path = os.path.dirname(__file__)
    return os.path.join(module_dir_path, *args)
    
    
class _MainHandler(RequestHandler):
    
    def get(self):
        self.render('index.html')
        
        
class _RecordingDemoHandler(RequestHandler):
    
    def initialize(self, sounds_dir_path):
        self._kwargs = {
            'sounds_dir_path': sounds_dir_path,
            'sound_names': _get_sound_names(sounds_dir_path)
        }
        
    def get(self):
        self.render('recording_demo.html', **self._kwargs)
        
        
def _get_sound_names(dir_path):
    # We assume in the following that there is only one directory
    # to visit.
    for (_, _, file_names) in os.walk(dir_path):
        return [
            file_name[:-len(_SOUND_FILE_NAME_EXTENSION)]
            for file_name in file_names
            if file_name.endswith(_SOUND_FILE_NAME_EXTENSION)]
            

class _RecordingDemoNewHandler(RequestHandler):
    
    def initialize(self, sounds_dir_path):
        self._sounds_dir_path = sounds_dir_path
   
    def get(self):
        self.render('recording_demo_new.html')
        
        
class _SoundsHandler(RequestHandler):
    
    def initialize(self, sounds_dir_path):
        self._sound_names = _get_sound_names(sounds_dir_path)
        
    def get(self):
        if len(self._sound_names) == 0:
            self.write('No sounds.')
        else:
            self.render('sounds.html', sound_names=self._sound_names)


class _SoundHandler(RequestHandler):
    
    def initialize(self, sounds_dir_path):
        self._sounds_dir_path = sounds_dir_path
        
    def get(self, sound_name):
        self.render('sound.html', sound_name=sound_name)


class _SoundFileHandler(RequestHandler):
    
    def initialize(self, sounds_dir_path):
        self._sounds_dir_path = sounds_dir_path
        
    def get(self, name):
        path = os.path.join(self._sounds_dir_path, name)
        with open(path, 'rb') as file_:
            data = file_.read()
        self.write(data)
        self.set_header('Content-Type', 'audio/wav')
        