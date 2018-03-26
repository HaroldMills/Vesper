"""
Shows information about a .wav file, including information about each of
its chunks.
"""


import wave


_FILE_PATH = (
    '/Users/harold/Downloads/Ridge_20141022/RIDGE_20141023_082704.wav')


def _main():
    
    _show_num_frames()
    _show_chunks()
    
    
def _show_num_frames():
    
    with wave.open(_FILE_PATH, 'rb') as reader:
        p = reader.getparams()
        print(
            'wave module says file has {} sample frames in {} bytes'.format(
                p.nframes, p.nframes * p.sampwidth))
        
        
def _show_chunks():
    
    with open(_FILE_PATH, 'rb') as f:
        
        file_size = _read_file_header(f)
        
        print('WAVE format subchunk IDs and sizes:')
        offset = 12
        while offset != file_size:
            f.seek(offset)
            chunk_id, chunk_size = _read_chunk_header(f)
            print('    "{}" {}'.format(chunk_id, chunk_size))
            offset += chunk_size + 8
        
        
def _read_file_header(f):
    _read_id(f, 'RIFF')
    file_size = _read_int32(f) + 8
    _read_id(f, 'WAVE')
    return file_size
    

def _read_id(f, expected=None):
    
    # Read ID.
    data = f.read(4)
    id_ = ''.join([chr(d) for d in data])
    
    # Check ID if indicated.
    if expected is not None and id_ != expected:
        raise ValueError('Expected ID "{}" not found.'.format(id_))
    
    else:
        return id_
        

def _read_int32(f):
    bytes_ = reversed(f.read(4))
    i = 0
    for b in bytes_:
        i = i * 256 + b
    return i

    
def _read_chunk_header(f):
    chunk_id = _read_id(f)
    chunk_size = _read_int32(f)
    return chunk_id, chunk_size    
    
    
# def _read_header(reader, check_format=True):
#     
#     p = reader.getparams()
#         
#     sample_size = p.sampwidth * 8
# 
#     if check_format:
#         _check_wave_file_format(sample_size, p.comptype)
#     
#     sample_rate = float(p.framerate)
#     
#     return Bunch(
#         num_channels=p.nchannels,
#         length=p.nframes,
#         sample_size=sample_size,
#         sample_rate=sample_rate,
#         compression_type=p.comptype,
#         compression_name=p.compname)
    
    
if __name__ == '__main__':
    _main()
