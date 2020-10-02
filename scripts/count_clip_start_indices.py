import sqlite3
import sys


CLIP_COUNT_QUERY = 'select count(*) from vesper_clip'

NULL_CLIP_COUNT_QUERY = \
    'select count(*) from vesper_clip where start_index is null'


def main():
    
    db_file_path = sys.argv[1]
        
    print(f'For archive database "{db_file_path}":')
        
    connection = sqlite3.connect(db_file_path)
    
    with connection:
    
        cursor = connection.cursor()
        
        cursor.execute(CLIP_COUNT_QUERY)
        total_clip_count = cursor.fetchone()[0]
        
        cursor.execute(NULL_CLIP_COUNT_QUERY)
        null_clip_count = cursor.fetchone()[0]
        
        print(
            f'Database contains {total_clip_count} clips, of which '
            f'{null_clip_count} do not have start indices.')
            
    
if __name__ == '__main__':
    main()
