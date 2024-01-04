"""Module containing class `AudioFileProcessor`."""


class AudioFileProcessor:

    """
    Interface implemented by audio file processors used in conjunction
    with class `AudioFileWriter`.
    """


    def __init__(self, name, settings):
        self._name = name
        self._settings = settings


    @property
    def name(self):
        return self._name
    

    @property
    def settings(self):
        return self._settings
    

    async def process_file(self, recording_dir_path, audio_file_path):

        """
        Processes the specified audio file.

        `recording_dir_path` is absolute, and `audio_file_path` is
        relative to `recording_dir_path`. Both are provided instead
        of just an absolute audio file path since some processors
        need to know the recording directory path. An example of
        this is a processor that uploads audio files to a cloud
        storage service, duplicating the structure within the
        recording directory in the cloud.
        """

        raise NotImplementedError()
