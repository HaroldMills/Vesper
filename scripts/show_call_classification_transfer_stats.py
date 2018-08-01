"""
Script that shows statistics computed from logs of Vesper commands that
transfer call classifications from the clips of one detector to those
of another.
"""


from pathlib import Path


LOG_DIR_PATH = Path(
    '/Users/harold/Desktop/NFC/Data/MPG Ranch/2017 MPG Ranch Archive/'
    'Logs/Jobs')


def main():
    show_stats('PNF 2018 Baseline Thrush Detector 1.0', 357)
    show_stats('PNF 2018 Baseline Tseep Detector 1.0', 358)
    show_stats('PNF Thrush Energy Detector 1.0', 353)
    show_stats('PNF Tseep Energy Detector 1.0', 354)
    
    
def show_stats(detector_name, job_num):
    
    print('{}:'.format(detector_name))
    
    file_name = 'Job {}.log'.format(job_num)
    file_path = LOG_DIR_PATH / file_name
    
    with open(file_path, 'r') as file_:
        
        lines = file_.read().strip().split('\n')
        
        total_num_original_calls = 0
        total_num_clips = 0
        total_num_transferred_calls = 0
        
        for line in lines:
            
            parts = line.split('/')
            
            if len(parts) == 5:
                
                parts = parts[-1].strip().split()
                num_original_calls = int(parts[0])
                num_clips = int(parts[1])
                num_transferred_calls = int(parts[2])
                
                if num_original_calls != 0 and num_clips != 0:
                    print(line)
                    total_num_original_calls += num_original_calls
                    total_num_clips += num_clips
                    total_num_transferred_calls += num_transferred_calls
                    
        percent = 100 * total_num_transferred_calls / \
            total_num_original_calls
            
        print((
            'Transferred {} of {} call classifications, '
            'a total of {:.1f} percent.').format(
                total_num_transferred_calls, total_num_original_calls,
                percent))
        
        precision = 100 * total_num_transferred_calls / total_num_clips
        
        print(
            'Precision of transferred call clips is {:.1f} percent.'.format(
                precision))


if __name__ == '__main__':
    main()
