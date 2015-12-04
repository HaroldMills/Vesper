"""Module containing utility functions pertaining to bat data."""


import pandas as pd


_KPRO_SPECIES_COLUMN_NAME = 'AUTO ID'
_SONOBAT_SPECIES_COLUMN_NAME = 'Consensus'


def merge_kpro_and_sonobat_data(kpro, sonobat):
    
    """
    Merges KPro and SonoBat dataframes.
    
    The resulting dataframe contains two columns, `file_name_base`
    and `species`.
    """
    
    # Eliminate rows without classifications.
    kpro = kpro[kpro[_KPRO_SPECIES_COLUMN_NAME] != 'NoID']
    sonobat = sonobat[sonobat[_SONOBAT_SPECIES_COLUMN_NAME].notnull()]
    
    # Add file name base column to `sonobat`.
    sonobat['file_name_base'] = \
        sonobat['Filename'].apply(_get_file_name_base)
        
    # Merge by file name base.
    merged = pd.merge(
        kpro, sonobat, left_on='OUT FILE', right_on='file_name_base')
    
    # Add lower case species code columns.
    merged['kpro_species'] = _lower(merged[_KPRO_SPECIES_COLUMN_NAME])
    merged['sonobat_species'] = _lower(merged[_SONOBAT_SPECIES_COLUMN_NAME])
    
    # Eliminate rows with different KPro and SonoBat classifications.
    merged = merged[merged['kpro_species'] == merged['sonobat_species']]
    
    # Retain only the columns that interest us.
    merged = merged[['file_name_base', 'kpro_species']]
    merged.rename(columns={'kpro_species': 'species'}, inplace=True)
    
    return merged

    
def _get_file_name_base(name):
    
    parts = name.split('_')
    
    if not parts[-1].endswith('.wav'):
        raise ValueError(
            'File name "{}" does not end in "{}".'.format(name, '.wav'))
        
    # Strip file name extension and optional species code.
    parts[-1] = parts[-1][:-4].split('-')[0]
    
    return '_'.join(parts)


def _lower(series):
    return series.apply(lambda s: s.lower())
