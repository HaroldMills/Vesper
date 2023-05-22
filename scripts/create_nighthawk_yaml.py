from pathlib import Path
import csv


DATA_DIR_PATH = Path(__file__).parent / 'data' / 'Nighthawk Taxonomy'
EBIRD_TAXONOMY_FILE_PATH = DATA_DIR_PATH / 'ebird_taxonomy.csv'
IBP_TAXONOMY_FILE_PATH = DATA_DIR_PATH / 'IBP-AOS-LIST21.csv'
ORDERS_FILE_PATH = DATA_DIR_PATH / 'orders_select_v6.txt'
FAMILIES_FILE_PATH = DATA_DIR_PATH / 'families_select_v6.txt'
GROUPS_FILE_PATH = DATA_DIR_PATH / 'groups_select_v6.txt'
SPECIES_FILE_PATH = DATA_DIR_PATH / 'species_select_v6.txt'

ANNOTATION_CONSTRAINTS_SECTION_HEADER = '''
annotation_constraints:
'''.lstrip()

ANNOTATION_CONSTRAINT_HEADER = '''
    - name: Nighthawk {} Classification
      description: >
          All classifications, including call subclassifications, with
          {} species codes.
      type: Hierarchical Values
      extends: Coarse Classification
      values:
          - Call:
'''

ANNOTATION_CONSTRAINT_INDENTATION = ' ' * 14


def main():

    orders, families, species_codes, species_code_mapping, descriptions = \
        get_taxonomy(EBIRD_TAXONOMY_FILE_PATH, IBP_TAXONOMY_FILE_PATH)
    
    # print(f'orders: {len(orders)}')
    # for order in orders:
    #     print(f'    {order}')

    # print(f'families: {len(families)}')
    # for family in families:
    #     print(f'    {family}')

    # print(f'species_codes: {len(species_codes)}')

    # print('ebird_species_codes:')
    # ebird_species_codes = sorted(ibp_species_codes.keys())
    # for code in ebird_species_codes:
    #     print(f'    {code} -> {ibp_species_codes[code]}')

    create_annotation_constraint_yaml(species_code_mapping)
    # create_clip_album_commands_yaml(descriptions, species_code_mapping)


def create_annotation_constraint_yaml(species_code_mapping):
    print(ANNOTATION_CONSTRAINTS_SECTION_HEADER)
    create_annotation_constraint_yaml_aux('IBP', species_code_mapping)
    create_annotation_constraint_yaml_aux('eBird')


def create_annotation_constraint_yaml_aux(name, species_code_mapping=None):
    print(ANNOTATION_CONSTRAINT_HEADER.format(name, name))
    list_taxa('orders', ORDERS_FILE_PATH)
    list_taxa('families', FAMILIES_FILE_PATH)
    list_taxa('groups', GROUPS_FILE_PATH)
    list_taxa('species', SPECIES_FILE_PATH, species_code_mapping)


def list_taxa(title, taxon_file_path, mapping=None):

    print(f'{ANNOTATION_CONSTRAINT_INDENTATION}# {title}')

    taxa = get_taxa(taxon_file_path)
    for taxon in taxa:
        if mapping is not None:
            taxon = mapping.get(taxon, taxon)
        print(f'{ANNOTATION_CONSTRAINT_INDENTATION}- {taxon}')

    print()


def create_clip_album_commands_yaml(descriptions, species_code_mapping):

    list_taxon_commands(
        'Taxonomic order', ORDERS_FILE_PATH, command_prefix='+', taxon_prefix_length=5)

    list_taxon_commands(
        'Taxonomic family', FAMILIES_FILE_PATH, taxon_prefix_length=5,
        descriptions=descriptions, description_col_num=55)

    list_taxon_commands('Taxonomic group', GROUPS_FILE_PATH)

    list_taxon_commands(
        'IBP species code', SPECIES_FILE_PATH,
        taxon_mapping=species_code_mapping, descriptions=descriptions,
        description_col_num=50)
    
    list_taxon_commands(
        'eBird species code', SPECIES_FILE_PATH, descriptions=descriptions,
        description_col_num=50)


def list_taxon_commands(
        title, taxon_file_path, command_prefix='=', taxon_mapping=None,
        taxon_prefix_length=None, descriptions=None, description_col_num=None):

    taxa = get_taxa(taxon_file_path)

    if descriptions is None:
        descriptions = {}

    print(f'    # {title} clip annotation commands.')

    for taxon in taxa:

        if taxon_mapping is not None:
            taxon = taxon_mapping.get(taxon, taxon)

        if taxon_prefix_length is None:
            text = taxon
        else:
            text = taxon[:taxon_prefix_length]

        line = f'    {command_prefix}{text}: [annotate_clips, Call.{taxon}]'

        description = descriptions.get(taxon)

        if description is not None:
            line = line.ljust(description_col_num) + '# ' + description

        print(line)

    print()


# TODO: Use Pandas here.
def get_taxonomy(ebird_file_path, ibp_file_path):

    orders = set()
    families = set()
    species_codes = set()
    scientific_names = {}
    descriptions = {}

    with open(ebird_file_path, newline='') as file:

        reader = csv.DictReader(file)

        for s in reader:

            # orders
            if s['order'] != 'NA':
                orders.add(s['order'])

            # families
            if s['family'] != 'NA':
                family, description = s['family'].strip().split(maxsplit=1)
                families.add(family)
                descriptions[family] = description[1:-1]

            # species
            species_code = s['code']
            scientific_name = s['sci_name']
            common_name = s['name']
            species_codes.add(species_code)
            scientific_names[species_code] = scientific_name
            descriptions[species_code] = f'{common_name} ({scientific_name})'

    species_code_mapping = \
        get_species_code_mapping(scientific_names, ibp_file_path)
    
    for ebird_species_code, ibp_species_code in species_code_mapping.items():
        descriptions[ibp_species_code] = descriptions[ebird_species_code]

    return (
        sorted(orders),
        sorted(families),
        sorted(species_codes),
        species_code_mapping,
        descriptions)


def get_taxa(file_path):
    with open(file_path) as file:
        contents = file.read()
    return contents.strip().split('\n')


def get_species_code_mapping(scientific_names, ibp_file_path):

    # Get mapping from scientific names to IBP species codes.
    with open(ibp_file_path, newline='') as file:
        reader = csv.DictReader(file)
        ibp_species_codes = {s['SCINAME']: s['SPEC'] for s in reader}

    # Get mapping from eBird species codes to IBP species codes.
    result = {}
    for ebird_species_code, scientific_name in scientific_names.items():
        ibp_species_code = ibp_species_codes.get(scientific_name)
        if ibp_species_code is not None:
            result[ebird_species_code] = ibp_species_code

    return result

    
if __name__ == '__main__':
    main()
