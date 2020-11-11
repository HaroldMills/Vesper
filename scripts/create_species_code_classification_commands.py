"""
Script that creates four-letter bird species code clip album commands.

The script obtains the species codes from a file downloaded from the
Institute for Bird Populations on 2020-11-11. The download link was
http://birdpop.org/docs/misc/IBPAOU.zip.
"""


from pathlib import Path


CSV_FILE_PATH = \
    Path(__file__).parent / 'data/ibp_alpha_codes/IBP-Alpha-Codes20.csv'

SPECIES_CODE_INDEX = 1
COMMON_NAME_INDEX = 3

LEADING_COMMENT = '''
    # Four-letter bird species code commands. These commands were derived
    # from the file http://birdpop.org/docs/misc/IBPAOU.zip, downloaded
    # from the Institute for Bird Populations on 2020-11-11.
'''.rstrip()


def main():
    
    with open(CSV_FILE_PATH) as csv_file:
        lines = csv_file.read().strip().split('\n')
        
    # Get data rows as tuples.
    rows = [line.split(',') for line in lines[1:]]
    
    # Sort by common name.
    rows.sort(key=lambda r: r[COMMON_NAME_INDEX])
    
    print(LEADING_COMMENT)

    for row in rows:
        
        # For some reason, some lines of the file have six columns and
        # others have seven, but the following works in both cases.
        species_code = row[SPECIES_CODE_INDEX]
        common_name = row[COMMON_NAME_INDEX]
        
        print(
            f'    ={species_code}: [annotate_clips, Call.{species_code}]'
            f'    # {common_name}')
            
    
if __name__ == '__main__':
    main()
