"""
Shows information about a .wav file, including information about each of
its chunks.
"""


from pathlib import Path
import wave


FILE_PATHS = (
    Path('/Users/harold/Desktop/NFC/FLAC Test/FLOOD-21C_20180901_194500.wav'),
    Path('/Users/harold/Desktop/NFC/FLAC Test/bobo.wav')
)


def main():
    for path in FILE_PATHS:
        print(f'For file "{path.name}"...')
        show_num_frames(path)
        show_chunks(path)
    
    
def show_num_frames(file_path):
    
        with wave.open(str(file_path), 'rb') as reader:

            p = reader.getparams()
            byte_count = p.nframes * p.nchannels * p.sampwidth

            print(
                f'    Python wave module says file has {p.nframes} sample '
                f'frames in {byte_count} bytes.')
        
        
def show_chunks(file_path):
    
    with open(file_path, 'rb') as f:
        
        file_size = read_file_header(f)
        
        print('    WAVE format subchunk IDs and sizes:')
        offset = 12
        while offset != file_size:
            f.seek(offset)
            chunk_id, chunk_size = read_chunk_header(f)
            print(f'        "{chunk_id}" {chunk_size}')
            offset += chunk_size + 8
        
        
def read_file_header(f):
    read_id(f, 'RIFF')
    file_size = read_int32(f) + 8
    read_id(f, 'WAVE')
    return file_size
    

def read_id(f, expected=None):
    
    # Read ID.
    data = f.read(4)
    id_ = ''.join([chr(d) for d in data])
    
    # Check ID if indicated.
    if expected is not None and id_ != expected:
        raise ValueError(f'Expected ID "{id_}" not found.')
    
    else:
        return id_
        

def read_int32(f):
    bytes_ = reversed(f.read(4))
    i = 0
    for b in bytes_:
        i = i * 256 + b
    return i

    
def read_chunk_header(f):
    chunk_id = read_id(f)
    chunk_size = read_int32(f)
    return chunk_id, chunk_size    
    
    
if __name__ == '__main__':
    main()
