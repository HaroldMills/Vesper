"""Script that summarizes Skyfield test results."""


from pathlib import Path

import pandas as pd


RESULTS_DIR_PATH = Path(
    '/Users/harold/Desktop/NFC/Data/Astronomy/Skyfield Test Results')

DIFF_COUNT_FILE_PATH = RESULTS_DIR_PATH / 'Solar Event Difference Counts.csv'

UNMATCHED_EVENTS_FILE_PATH = RESULTS_DIR_PATH / 'Unmatched Solar Events.csv'

DIFF_COLUMN_NAMES = ['-2 Diffs', '-1 Diffs', '0 Diffs', '1 Diffs', '2 Diffs']


def main():
    
    df = pd.read_csv(DIFF_COUNT_FILE_PATH)
    
    summarize_matched_events(df, 'all solar')
    
    grid_df = get_grid_data(df)
    summarize_events(grid_df, 'lat/lon grid solar')
    
    ithaca_df = get_ithaca_data(df)
    summarize_events(ithaca_df, 'Ithaca solar')
    
    mpg_ranch_df = get_mpg_ranch_data(df)
    summarize_events(mpg_ranch_df, 'MPG Ranch solar')
    
    
def get_grid_data(df):
    
    """
    Prunes dataframe to rows whose longitudes are multiples of 60
    degrees and whose years are multiples of 10. This includes only
    lat/lon grid locations for which we have USNO data for all eight
    types of solar events.
    """
    
    bools = (df['Longitude'] % 60 == 0) & (df['Year'] % 10 == 0)
    return df[bools]
    

def get_ithaca_data(df):
    bools = df['Latitude'] == 42.45
    return df[bools]
    
    
def get_mpg_ranch_data(df):
    bools = df['Latitude'] == 46.7
    return df[bools]


def summarize_events(df, name):
    summarize_matched_events(df, name)
    summarize_unmatched_events(df, name)
    
    
def summarize_matched_events(df, name):
    
    print(f'Summary of matches of {name} Skyfield and USNO events:')
    print()
    
    diff_counts = df[DIFF_COLUMN_NAMES]
    counts_by_diff = diff_counts.sum(axis=0).to_numpy()
    total_count = counts_by_diff.sum()
    
    print(f'A total of {total_count} events matched.')
    print()
    
    print('Skyfield - USNO matched event counts by time difference:')
    for count in range(-2, 3):
        print(f'    {count}: {counts_by_diff[count + 2]}')
    print()
    
    total_count = counts_by_diff.sum()
    print(f'Difference counts as percentages of matched events:')
    percentages = 100 * counts_by_diff / total_count
    for count in range(-2, 3):
        print(f'     {count}: {percentages[count + 2]}')
    print()
    
    within_one_minute = percentages[1:4].sum()
    print(
        f'{within_one_minute} percent of matched events were within '
        f'one minute of each other.')
    
    print(f'{percentages[2]} percent of matched events were the same.')
    
    one_minute = percentages[1] + percentages[3]
    print(f'{one_minute} percent of matched events differed by one minute.')
    
    print()
    print()
    print()
    
    
def summarize_unmatched_events(df, name):
    
    matched_count = df[DIFF_COLUMN_NAMES].to_numpy().sum()
    print(
        f'Summary of unmatched {name} events (for comparison, '
        f'{matched_count} events matched):')
    print()
    
    group_by = df.groupby(['Latitude', 'Longitude'], as_index=False)
    
    usno_table = group_by['Unmatched USNO Events'].sum().pivot(
        'Latitude', 'Longitude')
    usno_count = usno_table.to_numpy().sum()
    
    print(
        f'A total of {usno_count} USNO events were not matched by '
        f'Skyfield events.')
    print()
    
    print(usno_table)
    print()
    
    sf_table = group_by['Unmatched Skyfield Events'].sum().pivot(
        'Latitude', 'Longitude')
    sf_count = sf_table.to_numpy().sum()
    
    print(
        f'A total of {sf_count} Skyfield events were not matched by '
        f'USNO events.')
    print()
    
    print(sf_table)
    print()
    
    print()
    print()
    
    
if __name__ == '__main__':
    main()
