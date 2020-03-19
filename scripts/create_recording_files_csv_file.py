from pathlib import Path
import wave


OUTPUT_FILE_NAME = 'Recording Files.csv'


def main():
    lines = create_output_file_lines()
    write_output_file(lines)
    
    
def create_output_file_lines():
    
    cwd = Path('.')
    paths = cwd.glob('**/*.wav')
    
    lines = []
    
    for p in paths:
        
        try:
            with wave.open(str(p), 'rb') as reader:
                params = reader.getparams()
                 
        except Exception:
            line = create_output_file_line(p.name)
            
        else:
            line = create_output_file_line(p.name, *params)
            
        lines.append(line)
        
    lines.sort()
        
    return lines
        
        
def create_output_file_line(
        file_name, channel_count='', sample_size='', sample_rate='',
        length='', comp_type='', comp_name=''):
    
    if sample_size != '':
        sample_size *= 8
    
    return (
        f'{file_name},{sample_rate},{length},{channel_count},'
        f'{sample_size},{comp_type},{comp_name}')
    
    
def write_output_file(lines):
    contents = '\n'.join(lines) + '\n'
    with open(OUTPUT_FILE_NAME, 'w') as f:
        f.write(contents)
        
            
if __name__ == '__main__':
    main()
