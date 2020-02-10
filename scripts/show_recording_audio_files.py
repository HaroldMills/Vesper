"""
Script that shows information about the recording files in one or
more directories.

Usage:

    python show_recording_files <recording directories>
"""


from pathlib import Path
import random
import sys
import wave


_SIMULATED_ERROR_PROBABILITY = 0
"""
Simulated recording file read error probability.

For normal operation set this to zero.
"""


def main():
    infos = get_recording_file_infos()
    show_recording_file_infos(infos)
    
    
def get_recording_file_infos():
    
    infos = []
    
    for arg in sys.argv[1:]:
        
        recording_dir_path = Path(arg)
    
        for file_path in recording_dir_path.glob('**/*.wav'):
            
            try:
                num_channels, sample_rate, length = \
                    get_wav_file_info(file_path)
                
            except Exception as e:
                class_name = e.__class__.__name__
                print(
                    f'Could not get info for recording file "{file_path}". '
                    f'Attempt raised {class_name} exception with message: '
                    f'{str(e)}.')
                
            else:
                info = (file_path, num_channels, sample_rate, length)
                infos.append(info)
                
    return infos


def get_wav_file_info(file_path):
    
    with wave.open(str(file_path), 'rb') as file_:
        num_channels = file_.getnchannels()
        sample_rate = file_.getframerate()
        length = file_.getnframes()
        
        if random.random() < _SIMULATED_ERROR_PROBABILITY:
            raise ValueError('Could not read wav file.')
    
    return num_channels, sample_rate, length


def show_recording_file_infos(infos):
    for file_path, num_channels, sample_rate, length in infos:
        print(f'"{file_path}",{num_channels},{sample_rate},{length}')
           
    
if __name__ == '__main__':
    main()
