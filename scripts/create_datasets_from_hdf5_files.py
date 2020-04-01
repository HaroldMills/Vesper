"""Creates coarse classifier training datasets from clip HDF5 files."""


from collections import defaultdict
from pathlib import Path
import itertools
import math
import os
import random
import resource
import time

import h5py
# import resampy
import tensorflow as tf

from vesper.util.bunch import Bunch
import vesper.util.os_utils as os_utils
import vesper.util.time_utils as time_utils
import vesper.signal.resampling_utils as resampling_utils
import vesper.util.yaml_utils as yaml_utils


# TODO: Support creating multiple datasets in one run.


DATASET_NAME_PREFIX = 'Thrush 600K'

CALL_TYPE = DATASET_NAME_PREFIX.split()[0]

DATASET_CONFIGS = yaml_utils.load('''

- dataset_name_prefix: Thrush 20K
  train_dataset_size: [10000, 10000]
  val_dataset_size: [2500, 2500]
  test_dataset_size: [2500, 2500]
  
- dataset_name_prefix: Thrush 100K
  train_dataset_size: [50000, 50000]
  val_dataset_size: [2500, 2500]
  test_dataset_size: [2500, 2500]
  
- dataset_name_prefix: Thrush 600K
  train_dataset_size: [300000, 300000]
  val_dataset_size: [3000, 3000]
  test_dataset_size: [3000, 3000]

- dataset_name_prefix: Tseep 20K
  train_dataset_size: [10000, 10000]
  val_dataset_size: [2500, 2500]
  test_dataset_size: [2500, 2500]
    
- dataset_name_prefix: Tseep 100K
  train_dataset_size: [50000, 50000]
  val_dataset_size: [2500, 2500]
  test_dataset_size: [2500, 2500]
  
- dataset_name_prefix: Tseep 850K
  train_dataset_size: [425000, 425000]
  val_dataset_size: [10000, 10000]
  test_dataset_size: [10000, 10000]
  
- dataset_name_prefix: Tseep 2.5M
  train_dataset_size: [1275000, 1275000]
  val_dataset_size: [10000, 10000]
  test_dataset_size: [10000, 10000]
  
''')


DATA_DIR_PATH = Path(
    '/Users/harold/Desktop/NFC/Data/Vesper ML/MPG Ranch Coarse Classifier 4.0')

INPUT_DIR_PATH = DATA_DIR_PATH / 'HDF5 Files' / CALL_TYPE

THRUSH_INPUT_FILE_NAMES = '''
Thrush_2017 MPG Ranch_Old Bird Redux 1.1_Angela_Call.h5
Thrush_2017 MPG Ranch_Old Bird Redux 1.1_Angela_Noise.h5
Thrush_2017 MPG Ranch_Old Bird Redux 1.1_Bear_Call.h5
Thrush_2017 MPG Ranch_Old Bird Redux 1.1_Bear_Noise.h5
Thrush_2017 MPG Ranch_Old Bird Redux 1.1_Bell Crossing_Call.h5
Thrush_2017 MPG Ranch_Old Bird Redux 1.1_Bell Crossing_Noise.h5
Thrush_2017 MPG Ranch_Old Bird Redux 1.1_Darby_Call.h5
Thrush_2017 MPG Ranch_Old Bird Redux 1.1_Darby_Noise.h5
Thrush_2017 MPG Ranch_Old Bird Redux 1.1_Dashiell_Call.h5
Thrush_2017 MPG Ranch_Old Bird Redux 1.1_Dashiell_Noise.h5
Thrush_2017 MPG Ranch_Old Bird Redux 1.1_Davies_Call.h5
Thrush_2017 MPG Ranch_Old Bird Redux 1.1_Davies_Noise.h5
Thrush_2017 MPG Ranch_Old Bird Redux 1.1_Deer Mountain_Call.h5
Thrush_2017 MPG Ranch_Old Bird Redux 1.1_Deer Mountain_Noise.h5
Thrush_2017 MPG Ranch_Old Bird Redux 1.1_Floodplain_Call.h5
Thrush_2017 MPG Ranch_Old Bird Redux 1.1_Floodplain_Noise.h5
Thrush_2017 MPG Ranch_Old Bird Redux 1.1_Florence_Call.h5
Thrush_2017 MPG Ranch_Old Bird Redux 1.1_Florence_Noise.h5
Thrush_2017 MPG Ranch_Old Bird Redux 1.1_KBK_Call.h5
Thrush_2017 MPG Ranch_Old Bird Redux 1.1_KBK_Noise.h5
Thrush_2017 MPG Ranch_Old Bird Redux 1.1_Lilo_Call.h5
Thrush_2017 MPG Ranch_Old Bird Redux 1.1_Lilo_Noise.h5
Thrush_2017 MPG Ranch_Old Bird Redux 1.1_MPG North_Call.h5
Thrush_2017 MPG Ranch_Old Bird Redux 1.1_MPG North_Noise.h5
Thrush_2017 MPG Ranch_Old Bird Redux 1.1_Nelson_Call.h5
Thrush_2017 MPG Ranch_Old Bird Redux 1.1_Nelson_Noise.h5
Thrush_2017 MPG Ranch_Old Bird Redux 1.1_Oxbow_Call.h5
Thrush_2017 MPG Ranch_Old Bird Redux 1.1_Oxbow_Noise.h5
Thrush_2017 MPG Ranch_Old Bird Redux 1.1_Powell_Call.h5
Thrush_2017 MPG Ranch_Old Bird Redux 1.1_Powell_Noise.h5
Thrush_2017 MPG Ranch_Old Bird Redux 1.1_Reed_Call.h5
Thrush_2017 MPG Ranch_Old Bird Redux 1.1_Reed_Noise.h5
Thrush_2017 MPG Ranch_Old Bird Redux 1.1_Ridge_Call.h5
Thrush_2017 MPG Ranch_Old Bird Redux 1.1_Ridge_Noise.h5
Thrush_2017 MPG Ranch_Old Bird Redux 1.1_Seeley_Call.h5
Thrush_2017 MPG Ranch_Old Bird Redux 1.1_Seeley_Noise.h5
Thrush_2017 MPG Ranch_Old Bird Redux 1.1_Sheep Camp_Call.h5
Thrush_2017 MPG Ranch_Old Bird Redux 1.1_Sheep Camp_Noise.h5
Thrush_2017 MPG Ranch_Old Bird Redux 1.1_St Mary_Call.h5
Thrush_2017 MPG Ranch_Old Bird Redux 1.1_St Mary_Noise.h5
Thrush_2017 MPG Ranch_Old Bird Redux 1.1_Sula Peak_Call.h5
Thrush_2017 MPG Ranch_Old Bird Redux 1.1_Sula Peak_Noise.h5
Thrush_2017 MPG Ranch_Old Bird Redux 1.1_Teller_Call.h5
Thrush_2017 MPG Ranch_Old Bird Redux 1.1_Teller_Noise.h5
Thrush_2017 MPG Ranch_Old Bird Redux 1.1_Troy_Call.h5
Thrush_2017 MPG Ranch_Old Bird Redux 1.1_Troy_Noise.h5
Thrush_2017 MPG Ranch_Old Bird Redux 1.1_Walnut_Call.h5
Thrush_2017 MPG Ranch_Old Bird Redux 1.1_Walnut_Noise.h5
Thrush_2017 MPG Ranch_Old Bird Redux 1.1_Weber_Call.h5
Thrush_2017 MPG Ranch_Old Bird Redux 1.1_Weber_Noise.h5
Thrush_2017 MPG Ranch_Old Bird Redux 1.1_Willow_Call.h5
Thrush_2017 MPG Ranch_Old Bird Redux 1.1_Willow_Noise.h5
Thrush_2018 MPG Ranch Part 1_Old Bird Redux 1.1_Angel_Call.h5
Thrush_2018 MPG Ranch Part 1_Old Bird Redux 1.1_Angel_Noise.h5
Thrush_2018 MPG Ranch Part 1_Old Bird Redux 1.1_Bear_Call.h5
Thrush_2018 MPG Ranch Part 1_Old Bird Redux 1.1_Bear_Noise.h5
Thrush_2018 MPG Ranch Part 1_Old Bird Redux 1.1_Bell Crossing_Call.h5
Thrush_2018 MPG Ranch Part 1_Old Bird Redux 1.1_Bell Crossing_Noise.h5
Thrush_2018 MPG Ranch Part 1_Old Bird Redux 1.1_Bivory_Call.h5
Thrush_2018 MPG Ranch Part 1_Old Bird Redux 1.1_Bivory_Noise.h5
Thrush_2018 MPG Ranch Part 1_Old Bird Redux 1.1_CB Ranch_Call.h5
Thrush_2018 MPG Ranch Part 1_Old Bird Redux 1.1_CB Ranch_Noise.h5
Thrush_2018 MPG Ranch Part 1_Old Bird Redux 1.1_Coki_Call.h5
Thrush_2018 MPG Ranch Part 1_Old Bird Redux 1.1_Coki_Noise.h5
Thrush_2018 MPG Ranch Part 1_Old Bird Redux 1.1_Cricket_Call.h5
Thrush_2018 MPG Ranch Part 1_Old Bird Redux 1.1_Cricket_Noise.h5
Thrush_2018 MPG Ranch Part 1_Old Bird Redux 1.1_Darby High School PC_Call.h5
Thrush_2018 MPG Ranch Part 1_Old Bird Redux 1.1_Darby High School PC_Noise.h5
Thrush_2018 MPG Ranch Part 1_Old Bird Redux 1.1_Darby High School Swift_Call.h5
Thrush_2018 MPG Ranch Part 1_Old Bird Redux 1.1_Darby High School Swift_Noise.h5
Thrush_2018 MPG Ranch Part 1_Old Bird Redux 1.1_Dashiell_Call.h5
Thrush_2018 MPG Ranch Part 1_Old Bird Redux 1.1_Dashiell_Noise.h5
Thrush_2018 MPG Ranch Part 1_Old Bird Redux 1.1_Deer Mountain Lookout_Call.h5
Thrush_2018 MPG Ranch Part 1_Old Bird Redux 1.1_Deer Mountain Lookout_Noise.h5
Thrush_2018 MPG Ranch Part 1_Old Bird Redux 1.1_DonnaRae_Call.h5
Thrush_2018 MPG Ranch Part 1_Old Bird Redux 1.1_DonnaRae_Noise.h5
Thrush_2018 MPG Ranch Part 1_Old Bird Redux 1.1_Dreamcatcher_Call.h5
Thrush_2018 MPG Ranch Part 1_Old Bird Redux 1.1_Dreamcatcher_Noise.h5
Thrush_2018 MPG Ranch Part 1_Old Bird Redux 1.1_Esmerelda_Call.h5
Thrush_2018 MPG Ranch Part 1_Old Bird Redux 1.1_Esmerelda_Noise.h5
Thrush_2018 MPG Ranch Part 1_Old Bird Redux 1.1_Evander_Call.h5
Thrush_2018 MPG Ranch Part 1_Old Bird Redux 1.1_Evander_Noise.h5
Thrush_2018 MPG Ranch Part 1_Old Bird Redux 1.1_Florence High School_Call.h5
Thrush_2018 MPG Ranch Part 1_Old Bird Redux 1.1_Florence High School_Noise.h5
Thrush_2018 MPG Ranch Part 1_Old Bird Redux 1.1_Grandpa's Pond_Call.h5
Thrush_2018 MPG Ranch Part 1_Old Bird Redux 1.1_Grandpa's Pond_Noise.h5
Thrush_2018 MPG Ranch Part 1_Old Bird Redux 1.1_IBO Lucky Peak_Call.h5
Thrush_2018 MPG Ranch Part 1_Old Bird Redux 1.1_IBO Lucky Peak_Noise.h5
Thrush_2018 MPG Ranch Part 1_Old Bird Redux 1.1_IBO River_Call.h5
Thrush_2018 MPG Ranch Part 1_Old Bird Redux 1.1_IBO River_Noise.h5
Thrush_2018 MPG Ranch Part 1_Old Bird Redux 1.1_JJ_Call.h5
Thrush_2018 MPG Ranch Part 1_Old Bird Redux 1.1_JJ_Noise.h5
Thrush_2018 MPG Ranch Part 1_Old Bird Redux 1.1_KBK_Call.h5
Thrush_2018 MPG Ranch Part 1_Old Bird Redux 1.1_KBK_Noise.h5
Thrush_2018 MPG Ranch Part 1_Old Bird Redux 1.1_Kate_Call.h5
Thrush_2018 MPG Ranch Part 1_Old Bird Redux 1.1_Kate_Noise.h5
Thrush_2018 MPG Ranch Part 1_Old Bird Redux 1.1_Lee Metcalf NWR_Call.h5
Thrush_2018 MPG Ranch Part 1_Old Bird Redux 1.1_Lee Metcalf NWR_Noise.h5
Thrush_2018 MPG Ranch Part 1_Old Bird Redux 1.1_Lilo_Call.h5
Thrush_2018 MPG Ranch Part 1_Old Bird Redux 1.1_Lilo_Noise.h5
Thrush_2018 MPG Ranch Part 1_Old Bird Redux 1.1_Lost Trail_Call.h5
Thrush_2018 MPG Ranch Part 1_Old Bird Redux 1.1_Lost Trail_Noise.h5
Thrush_2018 MPG Ranch Part 1_Old Bird Redux 1.1_MPG North_Call.h5
Thrush_2018 MPG Ranch Part 1_Old Bird Redux 1.1_MPG North_Noise.h5
Thrush_2018 MPG Ranch Part 1_Old Bird Redux 1.1_MPG Ranch Floodplain SM2_Call.h5
Thrush_2018 MPG Ranch Part 1_Old Bird Redux 1.1_MPG Ranch Floodplain SM2_Noise.h5
Thrush_2018 MPG Ranch Part 1_Old Bird Redux 1.1_MPG Ranch Floodplain Swift_Call.h5
Thrush_2018 MPG Ranch Part 1_Old Bird Redux 1.1_MPG Ranch Floodplain Swift_Noise.h5
Thrush_2018 MPG Ranch Part 1_Old Bird Redux 1.1_MPG Ranch Ridge_Call.h5
Thrush_2018 MPG Ranch Part 1_Old Bird Redux 1.1_MPG Ranch Ridge_Noise.h5
Thrush_2018 MPG Ranch Part 1_Old Bird Redux 1.1_MPG Ranch Sheep Camp_Call.h5
Thrush_2018 MPG Ranch Part 1_Old Bird Redux 1.1_MPG Ranch Sheep Camp_Noise.h5
Thrush_2018 MPG Ranch Part 1_Old Bird Redux 1.1_MPG Ranch Subdivision_Call.h5
Thrush_2018 MPG Ranch Part 1_Old Bird Redux 1.1_MPG Ranch Subdivision_Noise.h5
Thrush_2018 MPG Ranch Part 1_Old Bird Redux 1.1_MPG Ranch Zumwalt Ridge_Call.h5
Thrush_2018 MPG Ranch Part 1_Old Bird Redux 1.1_MPG Ranch Zumwalt Ridge_Noise.h5
Thrush_2018 MPG Ranch Part 1_Old Bird Redux 1.1_Max_Call.h5
Thrush_2018 MPG Ranch Part 1_Old Bird Redux 1.1_Max_Noise.h5
Thrush_2018 MPG Ranch Part 1_Old Bird Redux 1.1_Meadowlark_Call.h5
Thrush_2018 MPG Ranch Part 1_Old Bird Redux 1.1_Meadowlark_Noise.h5
Thrush_2018 MPG Ranch Part 1_Old Bird Redux 1.1_Mickey_Call.h5
Thrush_2018 MPG Ranch Part 1_Old Bird Redux 1.1_Mickey_Noise.h5
Thrush_2018 MPG Ranch Part 1_Old Bird Redux 1.1_Mitzi_Call.h5
Thrush_2018 MPG Ranch Part 1_Old Bird Redux 1.1_Mitzi_Noise.h5
Thrush_2018 MPG Ranch Part 1_Old Bird Redux 1.1_Molly_Call.h5
Thrush_2018 MPG Ranch Part 1_Old Bird Redux 1.1_Molly_Noise.h5
Thrush_2018 MPG Ranch Part 1_Old Bird Redux 1.1_Oxbow_Call.h5
Thrush_2018 MPG Ranch Part 1_Old Bird Redux 1.1_Oxbow_Noise.h5
Thrush_2018 MPG Ranch Part 1_Old Bird Redux 1.1_Panda_Call.h5
Thrush_2018 MPG Ranch Part 1_Old Bird Redux 1.1_Panda_Noise.h5
Thrush_2018 MPG Ranch Part 1_Old Bird Redux 1.1_Petey_Call.h5
Thrush_2018 MPG Ranch Part 1_Old Bird Redux 1.1_Petey_Noise.h5
Thrush_2018 MPG Ranch Part 1_Old Bird Redux 1.1_Pocket Gopher_Call.h5
Thrush_2018 MPG Ranch Part 1_Old Bird Redux 1.1_Pocket Gopher_Noise.h5
Thrush_2018 MPG Ranch Part 1_Old Bird Redux 1.1_Sadie-Kate_Call.h5
Thrush_2018 MPG Ranch Part 1_Old Bird Redux 1.1_Sadie-Kate_Noise.h5
Thrush_2018 MPG Ranch Part 1_Old Bird Redux 1.1_Sasquatch_Call.h5
Thrush_2018 MPG Ranch Part 1_Old Bird Redux 1.1_Sasquatch_Noise.h5
Thrush_2018 MPG Ranch Part 1_Old Bird Redux 1.1_Seeley High School_Call.h5
Thrush_2018 MPG Ranch Part 1_Old Bird Redux 1.1_Seeley High School_Noise.h5
Thrush_2018 MPG Ranch Part 1_Old Bird Redux 1.1_Sleeman_Call.h5
Thrush_2018 MPG Ranch Part 1_Old Bird Redux 1.1_Sleeman_Noise.h5
Thrush_2018 MPG Ranch Part 1_Old Bird Redux 1.1_Slocum_Call.h5
Thrush_2018 MPG Ranch Part 1_Old Bird Redux 1.1_Slocum_Noise.h5
Thrush_2018 MPG Ranch Part 1_Old Bird Redux 1.1_St Mary Lookout_Call.h5
Thrush_2018 MPG Ranch Part 1_Old Bird Redux 1.1_St Mary Lookout_Noise.h5
Thrush_2018 MPG Ranch Part 1_Old Bird Redux 1.1_Sula Peak Lookout_Call.h5
Thrush_2018 MPG Ranch Part 1_Old Bird Redux 1.1_Sula Peak Lookout_Noise.h5
Thrush_2018 MPG Ranch Part 1_Old Bird Redux 1.1_Sula Ranger Station_Call.h5
Thrush_2018 MPG Ranch Part 1_Old Bird Redux 1.1_Sula Ranger Station_Noise.h5
Thrush_2018 MPG Ranch Part 1_Old Bird Redux 1.1_Teller_Call.h5
Thrush_2018 MPG Ranch Part 1_Old Bird Redux 1.1_Teller_Noise.h5
Thrush_2018 MPG Ranch Part 1_Old Bird Redux 1.1_Walnut_Call.h5
Thrush_2018 MPG Ranch Part 1_Old Bird Redux 1.1_Walnut_Noise.h5
Thrush_2018 MPG Ranch Part 1_Old Bird Redux 1.1_Willow Mountain Lookout_Call.h5
Thrush_2018 MPG Ranch Part 1_Old Bird Redux 1.1_Willow Mountain Lookout_Noise.h5
Thrush_2018 MPG Ranch Part 1_Old Bird Redux 1.1_YVAS_Call.h5
Thrush_2018 MPG Ranch Part 1_Old Bird Redux 1.1_YVAS_Noise.h5
Thrush_2018 MPG Ranch Part 1_Old Bird Redux 1.1_Zuri_Call.h5
Thrush_2018 MPG Ranch Part 1_Old Bird Redux 1.1_Zuri_Noise.h5
Thrush_2018 MPG Ranch Part 2_Old Bird Redux 1.1_Angel_Call.h5
Thrush_2018 MPG Ranch Part 2_Old Bird Redux 1.1_Angel_Noise.h5
Thrush_2018 MPG Ranch Part 2_Old Bird Redux 1.1_Bear_Call.h5
Thrush_2018 MPG Ranch Part 2_Old Bird Redux 1.1_Bear_Noise.h5
Thrush_2018 MPG Ranch Part 2_Old Bird Redux 1.1_Bell Crossing_Call.h5
Thrush_2018 MPG Ranch Part 2_Old Bird Redux 1.1_Bell Crossing_Noise.h5
Thrush_2018 MPG Ranch Part 2_Old Bird Redux 1.1_Bivory_Call.h5
Thrush_2018 MPG Ranch Part 2_Old Bird Redux 1.1_Bivory_Noise.h5
Thrush_2018 MPG Ranch Part 2_Old Bird Redux 1.1_CB Ranch_Call.h5
Thrush_2018 MPG Ranch Part 2_Old Bird Redux 1.1_CB Ranch_Noise.h5
Thrush_2018 MPG Ranch Part 2_Old Bird Redux 1.1_Coki_Call.h5
Thrush_2018 MPG Ranch Part 2_Old Bird Redux 1.1_Coki_Noise.h5
Thrush_2018 MPG Ranch Part 2_Old Bird Redux 1.1_Cricket_Call.h5
Thrush_2018 MPG Ranch Part 2_Old Bird Redux 1.1_Cricket_Noise.h5
Thrush_2018 MPG Ranch Part 2_Old Bird Redux 1.1_Darby High School PC_Call.h5
Thrush_2018 MPG Ranch Part 2_Old Bird Redux 1.1_Darby High School PC_Noise.h5
Thrush_2018 MPG Ranch Part 2_Old Bird Redux 1.1_Dashiell_Call.h5
Thrush_2018 MPG Ranch Part 2_Old Bird Redux 1.1_Dashiell_Noise.h5
Thrush_2018 MPG Ranch Part 2_Old Bird Redux 1.1_Deer Mountain Lookout_Call.h5
Thrush_2018 MPG Ranch Part 2_Old Bird Redux 1.1_Deer Mountain Lookout_Noise.h5
Thrush_2018 MPG Ranch Part 2_Old Bird Redux 1.1_DonnaRae_Call.h5
Thrush_2018 MPG Ranch Part 2_Old Bird Redux 1.1_DonnaRae_Noise.h5
Thrush_2018 MPG Ranch Part 2_Old Bird Redux 1.1_Dreamcatcher_Call.h5
Thrush_2018 MPG Ranch Part 2_Old Bird Redux 1.1_Dreamcatcher_Noise.h5
Thrush_2018 MPG Ranch Part 2_Old Bird Redux 1.1_Esmerelda_Call.h5
Thrush_2018 MPG Ranch Part 2_Old Bird Redux 1.1_Esmerelda_Noise.h5
Thrush_2018 MPG Ranch Part 2_Old Bird Redux 1.1_Evander_Call.h5
Thrush_2018 MPG Ranch Part 2_Old Bird Redux 1.1_Evander_Noise.h5
Thrush_2018 MPG Ranch Part 2_Old Bird Redux 1.1_Florence High School_Call.h5
Thrush_2018 MPG Ranch Part 2_Old Bird Redux 1.1_Florence High School_Noise.h5
Thrush_2018 MPG Ranch Part 2_Old Bird Redux 1.1_Grandpa's Pond_Call.h5
Thrush_2018 MPG Ranch Part 2_Old Bird Redux 1.1_Grandpa's Pond_Noise.h5
Thrush_2018 MPG Ranch Part 2_Old Bird Redux 1.1_IBO Lucky Peak_Call.h5
Thrush_2018 MPG Ranch Part 2_Old Bird Redux 1.1_IBO Lucky Peak_Noise.h5
Thrush_2018 MPG Ranch Part 2_Old Bird Redux 1.1_IBO River_Call.h5
Thrush_2018 MPG Ranch Part 2_Old Bird Redux 1.1_IBO River_Noise.h5
Thrush_2018 MPG Ranch Part 2_Old Bird Redux 1.1_JJ_Call.h5
Thrush_2018 MPG Ranch Part 2_Old Bird Redux 1.1_JJ_Noise.h5
Thrush_2018 MPG Ranch Part 2_Old Bird Redux 1.1_KBK_Call.h5
Thrush_2018 MPG Ranch Part 2_Old Bird Redux 1.1_KBK_Noise.h5
Thrush_2018 MPG Ranch Part 2_Old Bird Redux 1.1_Kate_Call.h5
Thrush_2018 MPG Ranch Part 2_Old Bird Redux 1.1_Kate_Noise.h5
Thrush_2018 MPG Ranch Part 2_Old Bird Redux 1.1_Lee Metcalf NWR_Call.h5
Thrush_2018 MPG Ranch Part 2_Old Bird Redux 1.1_Lee Metcalf NWR_Noise.h5
Thrush_2018 MPG Ranch Part 2_Old Bird Redux 1.1_Lilo_Call.h5
Thrush_2018 MPG Ranch Part 2_Old Bird Redux 1.1_Lilo_Noise.h5
Thrush_2018 MPG Ranch Part 2_Old Bird Redux 1.1_Lost Trail_Call.h5
Thrush_2018 MPG Ranch Part 2_Old Bird Redux 1.1_Lost Trail_Noise.h5
Thrush_2018 MPG Ranch Part 2_Old Bird Redux 1.1_MPG North_Call.h5
Thrush_2018 MPG Ranch Part 2_Old Bird Redux 1.1_MPG North_Noise.h5
Thrush_2018 MPG Ranch Part 2_Old Bird Redux 1.1_MPG Ranch Floodplain_Call.h5
Thrush_2018 MPG Ranch Part 2_Old Bird Redux 1.1_MPG Ranch Floodplain_Noise.h5
Thrush_2018 MPG Ranch Part 2_Old Bird Redux 1.1_MPG Ranch Ridge_Call.h5
Thrush_2018 MPG Ranch Part 2_Old Bird Redux 1.1_MPG Ranch Ridge_Noise.h5
Thrush_2018 MPG Ranch Part 2_Old Bird Redux 1.1_MPG Ranch Sheep Camp_Call.h5
Thrush_2018 MPG Ranch Part 2_Old Bird Redux 1.1_MPG Ranch Sheep Camp_Noise.h5
Thrush_2018 MPG Ranch Part 2_Old Bird Redux 1.1_MPG Ranch Subdivision_Call.h5
Thrush_2018 MPG Ranch Part 2_Old Bird Redux 1.1_MPG Ranch Subdivision_Noise.h5
Thrush_2018 MPG Ranch Part 2_Old Bird Redux 1.1_MPG Ranch Zumwalt Ridge_Call.h5
Thrush_2018 MPG Ranch Part 2_Old Bird Redux 1.1_MPG Ranch Zumwalt Ridge_Noise.h5
Thrush_2018 MPG Ranch Part 2_Old Bird Redux 1.1_Max_Call.h5
Thrush_2018 MPG Ranch Part 2_Old Bird Redux 1.1_Max_Noise.h5
Thrush_2018 MPG Ranch Part 2_Old Bird Redux 1.1_Meadowlark_Call.h5
Thrush_2018 MPG Ranch Part 2_Old Bird Redux 1.1_Meadowlark_Noise.h5
Thrush_2018 MPG Ranch Part 2_Old Bird Redux 1.1_Mickey_Call.h5
Thrush_2018 MPG Ranch Part 2_Old Bird Redux 1.1_Mickey_Noise.h5
Thrush_2018 MPG Ranch Part 2_Old Bird Redux 1.1_Mitzi_Call.h5
Thrush_2018 MPG Ranch Part 2_Old Bird Redux 1.1_Mitzi_Noise.h5
Thrush_2018 MPG Ranch Part 2_Old Bird Redux 1.1_Molly_Call.h5
Thrush_2018 MPG Ranch Part 2_Old Bird Redux 1.1_Molly_Noise.h5
Thrush_2018 MPG Ranch Part 2_Old Bird Redux 1.1_Oxbow_Call.h5
Thrush_2018 MPG Ranch Part 2_Old Bird Redux 1.1_Oxbow_Noise.h5
Thrush_2018 MPG Ranch Part 2_Old Bird Redux 1.1_Panda_Call.h5
Thrush_2018 MPG Ranch Part 2_Old Bird Redux 1.1_Panda_Noise.h5
Thrush_2018 MPG Ranch Part 2_Old Bird Redux 1.1_Petey_Call.h5
Thrush_2018 MPG Ranch Part 2_Old Bird Redux 1.1_Petey_Noise.h5
Thrush_2018 MPG Ranch Part 2_Old Bird Redux 1.1_Pocket Gopher_Call.h5
Thrush_2018 MPG Ranch Part 2_Old Bird Redux 1.1_Pocket Gopher_Noise.h5
Thrush_2018 MPG Ranch Part 2_Old Bird Redux 1.1_Sadie-Kate_Call.h5
Thrush_2018 MPG Ranch Part 2_Old Bird Redux 1.1_Sadie-Kate_Noise.h5
Thrush_2018 MPG Ranch Part 2_Old Bird Redux 1.1_Sasquatch_Call.h5
Thrush_2018 MPG Ranch Part 2_Old Bird Redux 1.1_Sasquatch_Noise.h5
Thrush_2018 MPG Ranch Part 2_Old Bird Redux 1.1_Seeley High School_Call.h5
Thrush_2018 MPG Ranch Part 2_Old Bird Redux 1.1_Seeley High School_Noise.h5
Thrush_2018 MPG Ranch Part 2_Old Bird Redux 1.1_Sleeman_Call.h5
Thrush_2018 MPG Ranch Part 2_Old Bird Redux 1.1_Sleeman_Noise.h5
Thrush_2018 MPG Ranch Part 2_Old Bird Redux 1.1_Slocum_Call.h5
Thrush_2018 MPG Ranch Part 2_Old Bird Redux 1.1_Slocum_Noise.h5
Thrush_2018 MPG Ranch Part 2_Old Bird Redux 1.1_St Mary Lookout_Call.h5
Thrush_2018 MPG Ranch Part 2_Old Bird Redux 1.1_St Mary Lookout_Noise.h5
Thrush_2018 MPG Ranch Part 2_Old Bird Redux 1.1_Sula Peak Lookout_Call.h5
Thrush_2018 MPG Ranch Part 2_Old Bird Redux 1.1_Sula Peak Lookout_Noise.h5
Thrush_2018 MPG Ranch Part 2_Old Bird Redux 1.1_Sula Ranger Station_Call.h5
Thrush_2018 MPG Ranch Part 2_Old Bird Redux 1.1_Sula Ranger Station_Noise.h5
Thrush_2018 MPG Ranch Part 2_Old Bird Redux 1.1_Teller_Call.h5
Thrush_2018 MPG Ranch Part 2_Old Bird Redux 1.1_Teller_Noise.h5
Thrush_2018 MPG Ranch Part 2_Old Bird Redux 1.1_Walnut_Call.h5
Thrush_2018 MPG Ranch Part 2_Old Bird Redux 1.1_Walnut_Noise.h5
Thrush_2018 MPG Ranch Part 2_Old Bird Redux 1.1_Willow Mountain Lookout_Call.h5
Thrush_2018 MPG Ranch Part 2_Old Bird Redux 1.1_Willow Mountain Lookout_Noise.h5
Thrush_2018 MPG Ranch Part 2_Old Bird Redux 1.1_YVAS_Call.h5
Thrush_2018 MPG Ranch Part 2_Old Bird Redux 1.1_YVAS_Noise.h5
Thrush_2018 MPG Ranch Part 2_Old Bird Redux 1.1_Zuri_Call.h5
Thrush_2018 MPG Ranch Part 2_Old Bird Redux 1.1_Zuri_Noise.h5
Thrush_2018-08 MPG Ranch Noises_MPG Ranch 0.0_Angel_Noise.h5
Thrush_2018-08 MPG Ranch Noises_MPG Ranch 0.0_Bear_Noise.h5
Thrush_2018-08 MPG Ranch Noises_MPG Ranch 0.0_Bell Crossing_Noise.h5
Thrush_2018-08 MPG Ranch Noises_MPG Ranch 0.0_Bivory_Noise.h5
Thrush_2018-08 MPG Ranch Noises_MPG Ranch 0.0_CB Ranch_Noise.h5
Thrush_2018-08 MPG Ranch Noises_MPG Ranch 0.0_Coki_Noise.h5
Thrush_2018-08 MPG Ranch Noises_MPG Ranch 0.0_Cricket_Noise.h5
Thrush_2018-08 MPG Ranch Noises_MPG Ranch 0.0_Darby High School PC_Noise.h5
Thrush_2018-08 MPG Ranch Noises_MPG Ranch 0.0_Darby High School Swift_Noise.h5
Thrush_2018-08 MPG Ranch Noises_MPG Ranch 0.0_Dashiell_Noise.h5
Thrush_2018-08 MPG Ranch Noises_MPG Ranch 0.0_Deer Mountain Lookout_Noise.h5
Thrush_2018-08 MPG Ranch Noises_MPG Ranch 0.0_DonnaRae_Noise.h5
Thrush_2018-08 MPG Ranch Noises_MPG Ranch 0.0_Dreamcatcher_Noise.h5
Thrush_2018-08 MPG Ranch Noises_MPG Ranch 0.0_Esmerelda_Noise.h5
Thrush_2018-08 MPG Ranch Noises_MPG Ranch 0.0_Evander_Noise.h5
Thrush_2018-08 MPG Ranch Noises_MPG Ranch 0.0_Florence High School_Noise.h5
Thrush_2018-08 MPG Ranch Noises_MPG Ranch 0.0_Grandpa's Pond_Noise.h5
Thrush_2018-08 MPG Ranch Noises_MPG Ranch 0.0_IBO Lucky Peak_Noise.h5
Thrush_2018-08 MPG Ranch Noises_MPG Ranch 0.0_IBO River_Noise.h5
Thrush_2018-08 MPG Ranch Noises_MPG Ranch 0.0_JJ_Noise.h5
Thrush_2018-08 MPG Ranch Noises_MPG Ranch 0.0_KBK_Noise.h5
Thrush_2018-08 MPG Ranch Noises_MPG Ranch 0.0_Kate_Noise.h5
Thrush_2018-08 MPG Ranch Noises_MPG Ranch 0.0_Lee Metcalf NWR_Noise.h5
Thrush_2018-08 MPG Ranch Noises_MPG Ranch 0.0_Lilo_Noise.h5
Thrush_2018-08 MPG Ranch Noises_MPG Ranch 0.0_Lost Trail_Noise.h5
Thrush_2018-08 MPG Ranch Noises_MPG Ranch 0.0_MPG North_Noise.h5
Thrush_2018-08 MPG Ranch Noises_MPG Ranch 0.0_MPG Ranch Floodplain SM2_Noise.h5
Thrush_2018-08 MPG Ranch Noises_MPG Ranch 0.0_MPG Ranch Floodplain Swift_Noise.h5
Thrush_2018-08 MPG Ranch Noises_MPG Ranch 0.0_MPG Ranch Ridge_Noise.h5
Thrush_2018-08 MPG Ranch Noises_MPG Ranch 0.0_MPG Ranch Sheep Camp_Noise.h5
Thrush_2018-08 MPG Ranch Noises_MPG Ranch 0.0_MPG Ranch Subdivision_Noise.h5
Thrush_2018-08 MPG Ranch Noises_MPG Ranch 0.0_MPG Ranch Zumwalt Ridge_Noise.h5
Thrush_2018-08 MPG Ranch Noises_MPG Ranch 0.0_Max_Noise.h5
Thrush_2018-08 MPG Ranch Noises_MPG Ranch 0.0_Meadowlark_Noise.h5
Thrush_2018-08 MPG Ranch Noises_MPG Ranch 0.0_Mickey_Noise.h5
Thrush_2018-08 MPG Ranch Noises_MPG Ranch 0.0_Mitzi_Noise.h5
Thrush_2018-08 MPG Ranch Noises_MPG Ranch 0.0_Molly_Noise.h5
Thrush_2018-08 MPG Ranch Noises_MPG Ranch 0.0_Oxbow_Noise.h5
Thrush_2018-08 MPG Ranch Noises_MPG Ranch 0.0_Panda_Noise.h5
Thrush_2018-08 MPG Ranch Noises_MPG Ranch 0.0_Petey_Noise.h5
Thrush_2018-08 MPG Ranch Noises_MPG Ranch 0.0_Pocket Gopher_Noise.h5
Thrush_2018-08 MPG Ranch Noises_MPG Ranch 0.0_Sadie-Kate_Noise.h5
Thrush_2018-08 MPG Ranch Noises_MPG Ranch 0.0_Sasquatch_Noise.h5
Thrush_2018-08 MPG Ranch Noises_MPG Ranch 0.0_Seeley High School_Noise.h5
Thrush_2018-08 MPG Ranch Noises_MPG Ranch 0.0_Sleeman_Noise.h5
Thrush_2018-08 MPG Ranch Noises_MPG Ranch 0.0_Slocum_Noise.h5
Thrush_2018-08 MPG Ranch Noises_MPG Ranch 0.0_St Mary Lookout_Noise.h5
Thrush_2018-08 MPG Ranch Noises_MPG Ranch 0.0_Sula Peak Lookout_Noise.h5
Thrush_2018-08 MPG Ranch Noises_MPG Ranch 0.0_Sula Ranger Station_Noise.h5
Thrush_2018-08 MPG Ranch Noises_MPG Ranch 0.0_Teller_Noise.h5
Thrush_2018-08 MPG Ranch Noises_MPG Ranch 0.0_Walnut_Noise.h5
Thrush_2018-08 MPG Ranch Noises_MPG Ranch 0.0_Willow Mountain Lookout_Noise.h5
Thrush_2018-08 MPG Ranch Noises_MPG Ranch 0.0_YVAS_Noise.h5
Thrush_2018-08 MPG Ranch Noises_MPG Ranch 0.0_Zuri_Noise.h5
Thrush_2018-09 MPG Ranch Noises_MPG Ranch 0.0_Angel_Noise.h5
Thrush_2018-09 MPG Ranch Noises_MPG Ranch 0.0_Bear_Noise.h5
Thrush_2018-09 MPG Ranch Noises_MPG Ranch 0.0_Bell Crossing_Noise.h5
Thrush_2018-09 MPG Ranch Noises_MPG Ranch 0.0_Bivory_Noise.h5
Thrush_2018-09 MPG Ranch Noises_MPG Ranch 0.0_CB Ranch_Noise.h5
Thrush_2018-09 MPG Ranch Noises_MPG Ranch 0.0_Coki_Noise.h5
Thrush_2018-09 MPG Ranch Noises_MPG Ranch 0.0_Cricket_Noise.h5
Thrush_2018-09 MPG Ranch Noises_MPG Ranch 0.0_Darby High School PC_Noise.h5
Thrush_2018-09 MPG Ranch Noises_MPG Ranch 0.0_Dashiell_Noise.h5
Thrush_2018-09 MPG Ranch Noises_MPG Ranch 0.0_Deer Mountain Lookout_Noise.h5
Thrush_2018-09 MPG Ranch Noises_MPG Ranch 0.0_DonnaRae_Noise.h5
Thrush_2018-09 MPG Ranch Noises_MPG Ranch 0.0_Dreamcatcher_Noise.h5
Thrush_2018-09 MPG Ranch Noises_MPG Ranch 0.0_Esmerelda_Noise.h5
Thrush_2018-09 MPG Ranch Noises_MPG Ranch 0.0_Evander_Noise.h5
Thrush_2018-09 MPG Ranch Noises_MPG Ranch 0.0_Florence High School_Noise.h5
Thrush_2018-09 MPG Ranch Noises_MPG Ranch 0.0_Grandpa's Pond_Noise.h5
Thrush_2018-09 MPG Ranch Noises_MPG Ranch 0.0_IBO Lucky Peak_Noise.h5
Thrush_2018-09 MPG Ranch Noises_MPG Ranch 0.0_IBO River_Noise.h5
Thrush_2018-09 MPG Ranch Noises_MPG Ranch 0.0_JJ_Noise.h5
Thrush_2018-09 MPG Ranch Noises_MPG Ranch 0.0_KBK_Noise.h5
Thrush_2018-09 MPG Ranch Noises_MPG Ranch 0.0_Kate_Noise.h5
Thrush_2018-09 MPG Ranch Noises_MPG Ranch 0.0_Lee Metcalf NWR_Noise.h5
Thrush_2018-09 MPG Ranch Noises_MPG Ranch 0.0_Lilo_Noise.h5
Thrush_2018-09 MPG Ranch Noises_MPG Ranch 0.0_Lost Trail_Noise.h5
Thrush_2018-09 MPG Ranch Noises_MPG Ranch 0.0_MPG North_Noise.h5
Thrush_2018-09 MPG Ranch Noises_MPG Ranch 0.0_MPG Ranch Floodplain_Noise.h5
Thrush_2018-09 MPG Ranch Noises_MPG Ranch 0.0_MPG Ranch Ridge_Noise.h5
Thrush_2018-09 MPG Ranch Noises_MPG Ranch 0.0_MPG Ranch Sheep Camp_Noise.h5
Thrush_2018-09 MPG Ranch Noises_MPG Ranch 0.0_MPG Ranch Subdivision_Noise.h5
Thrush_2018-09 MPG Ranch Noises_MPG Ranch 0.0_MPG Ranch Zumwalt Ridge_Noise.h5
Thrush_2018-09 MPG Ranch Noises_MPG Ranch 0.0_Max_Noise.h5
Thrush_2018-09 MPG Ranch Noises_MPG Ranch 0.0_Meadowlark_Noise.h5
Thrush_2018-09 MPG Ranch Noises_MPG Ranch 0.0_Mickey_Noise.h5
Thrush_2018-09 MPG Ranch Noises_MPG Ranch 0.0_Mitzi_Noise.h5
Thrush_2018-09 MPG Ranch Noises_MPG Ranch 0.0_Molly_Noise.h5
Thrush_2018-09 MPG Ranch Noises_MPG Ranch 0.0_Oxbow_Noise.h5
Thrush_2018-09 MPG Ranch Noises_MPG Ranch 0.0_Panda_Noise.h5
Thrush_2018-09 MPG Ranch Noises_MPG Ranch 0.0_Petey_Noise.h5
Thrush_2018-09 MPG Ranch Noises_MPG Ranch 0.0_Pocket Gopher_Noise.h5
Thrush_2018-09 MPG Ranch Noises_MPG Ranch 0.0_Sadie-Kate_Noise.h5
Thrush_2018-09 MPG Ranch Noises_MPG Ranch 0.0_Sasquatch_Noise.h5
Thrush_2018-09 MPG Ranch Noises_MPG Ranch 0.0_Seeley High School_Noise.h5
Thrush_2018-09 MPG Ranch Noises_MPG Ranch 0.0_Sleeman_Noise.h5
Thrush_2018-09 MPG Ranch Noises_MPG Ranch 0.0_Slocum_Noise.h5
Thrush_2018-09 MPG Ranch Noises_MPG Ranch 0.0_St Mary Lookout_Noise.h5
Thrush_2018-09 MPG Ranch Noises_MPG Ranch 0.0_Sula Peak Lookout_Noise.h5
Thrush_2018-09 MPG Ranch Noises_MPG Ranch 0.0_Sula Ranger Station_Noise.h5
Thrush_2018-09 MPG Ranch Noises_MPG Ranch 0.0_Teller_Noise.h5
Thrush_2018-09 MPG Ranch Noises_MPG Ranch 0.0_Walnut_Noise.h5
Thrush_2018-09 MPG Ranch Noises_MPG Ranch 0.0_Willow Mountain Lookout_Noise.h5
Thrush_2018-09 MPG Ranch Noises_MPG Ranch 0.0_YVAS_Noise.h5
Thrush_2018-09 MPG Ranch Noises_MPG Ranch 0.0_Zuri_Noise.h5
'''.strip().split('\n')
"""
Thrush dataset input HDF5 file names.

The input HDF5 files for the Heron Crossing station (which operated in
2018 but not 2017) are omitted from this list since its recordings are
contaminated with audio from a commercial radio station, which we do not
wish to attempt to train for.
"""

# THRUSH_INPUT_FILE_NAMES = '''
# Thrush_2018 MPG Ranch Part 1_Old Bird Redux 1.1_Angel_Call.h5
# Thrush_2018 MPG Ranch Part 1_Old Bird Redux 1.1_Angel_Noise.h5
# Thrush_2018 MPG Ranch Part 1_Old Bird Redux 1.1_Bear_Call.h5
# Thrush_2018 MPG Ranch Part 1_Old Bird Redux 1.1_Bear_Noise.h5
# Thrush_2018 MPG Ranch Part 1_Old Bird Redux 1.1_Bell Crossing_Call.h5
# Thrush_2018 MPG Ranch Part 1_Old Bird Redux 1.1_Bell Crossing_Noise.h5
# Thrush_2018 MPG Ranch Part 1_Old Bird Redux 1.1_Bivory_Call.h5
# Thrush_2018 MPG Ranch Part 1_Old Bird Redux 1.1_Bivory_Noise.h5
# Thrush_2018 MPG Ranch Part 1_Old Bird Redux 1.1_CB Ranch_Call.h5
# Thrush_2018 MPG Ranch Part 1_Old Bird Redux 1.1_CB Ranch_Noise.h5
# Thrush_2018 MPG Ranch Part 1_Old Bird Redux 1.1_Coki_Call.h5
# Thrush_2018 MPG Ranch Part 1_Old Bird Redux 1.1_Coki_Noise.h5
# Thrush_2018 MPG Ranch Part 1_Old Bird Redux 1.1_Cricket_Call.h5
# Thrush_2018 MPG Ranch Part 1_Old Bird Redux 1.1_Cricket_Noise.h5
# '''.strip().split('\n')

TSEEP_INPUT_FILE_NAMES = '''
Tseep_2017 MPG Ranch_Old Bird Redux 1.1_Angela_CHSP-DEJU.h5
Tseep_2017 MPG Ranch_Old Bird Redux 1.1_Angela_Call.h5
Tseep_2017 MPG Ranch_Old Bird Redux 1.1_Angela_Noise.h5
Tseep_2017 MPG Ranch_Old Bird Redux 1.1_Angela_Tone.h5
Tseep_2017 MPG Ranch_Old Bird Redux 1.1_Bear_CHSP-DEJU.h5
Tseep_2017 MPG Ranch_Old Bird Redux 1.1_Bear_Call.h5
Tseep_2017 MPG Ranch_Old Bird Redux 1.1_Bear_Noise.h5
Tseep_2017 MPG Ranch_Old Bird Redux 1.1_Bear_Tone.h5
Tseep_2017 MPG Ranch_Old Bird Redux 1.1_Bell Crossing_CHSP-DEJU.h5
Tseep_2017 MPG Ranch_Old Bird Redux 1.1_Bell Crossing_Call.h5
Tseep_2017 MPG Ranch_Old Bird Redux 1.1_Bell Crossing_Noise.h5
Tseep_2017 MPG Ranch_Old Bird Redux 1.1_Bell Crossing_Tone.h5
Tseep_2017 MPG Ranch_Old Bird Redux 1.1_Darby_CHSP-DEJU.h5
Tseep_2017 MPG Ranch_Old Bird Redux 1.1_Darby_Call.h5
Tseep_2017 MPG Ranch_Old Bird Redux 1.1_Darby_Noise.h5
Tseep_2017 MPG Ranch_Old Bird Redux 1.1_Darby_Tone.h5
Tseep_2017 MPG Ranch_Old Bird Redux 1.1_Dashiell_CHSP-DEJU.h5
Tseep_2017 MPG Ranch_Old Bird Redux 1.1_Dashiell_Call.h5
Tseep_2017 MPG Ranch_Old Bird Redux 1.1_Dashiell_Noise.h5
Tseep_2017 MPG Ranch_Old Bird Redux 1.1_Dashiell_Tone.h5
Tseep_2017 MPG Ranch_Old Bird Redux 1.1_Davies_CHSP-DEJU.h5
Tseep_2017 MPG Ranch_Old Bird Redux 1.1_Davies_Call.h5
Tseep_2017 MPG Ranch_Old Bird Redux 1.1_Davies_Noise.h5
Tseep_2017 MPG Ranch_Old Bird Redux 1.1_Davies_Tone.h5
Tseep_2017 MPG Ranch_Old Bird Redux 1.1_Deer Mountain_CHSP-DEJU.h5
Tseep_2017 MPG Ranch_Old Bird Redux 1.1_Deer Mountain_Call.h5
Tseep_2017 MPG Ranch_Old Bird Redux 1.1_Deer Mountain_Noise.h5
Tseep_2017 MPG Ranch_Old Bird Redux 1.1_Deer Mountain_Tone.h5
Tseep_2017 MPG Ranch_Old Bird Redux 1.1_Floodplain_CHSP-DEJU.h5
Tseep_2017 MPG Ranch_Old Bird Redux 1.1_Floodplain_Call.h5
Tseep_2017 MPG Ranch_Old Bird Redux 1.1_Floodplain_Noise.h5
Tseep_2017 MPG Ranch_Old Bird Redux 1.1_Floodplain_Tone.h5
Tseep_2017 MPG Ranch_Old Bird Redux 1.1_Florence_CHSP-DEJU.h5
Tseep_2017 MPG Ranch_Old Bird Redux 1.1_Florence_Call.h5
Tseep_2017 MPG Ranch_Old Bird Redux 1.1_Florence_Noise.h5
Tseep_2017 MPG Ranch_Old Bird Redux 1.1_Florence_Tone.h5
Tseep_2017 MPG Ranch_Old Bird Redux 1.1_KBK_CHSP-DEJU.h5
Tseep_2017 MPG Ranch_Old Bird Redux 1.1_KBK_Call.h5
Tseep_2017 MPG Ranch_Old Bird Redux 1.1_KBK_Noise.h5
Tseep_2017 MPG Ranch_Old Bird Redux 1.1_KBK_Tone.h5
Tseep_2017 MPG Ranch_Old Bird Redux 1.1_Lilo_CHSP-DEJU.h5
Tseep_2017 MPG Ranch_Old Bird Redux 1.1_Lilo_Call.h5
Tseep_2017 MPG Ranch_Old Bird Redux 1.1_Lilo_Noise.h5
Tseep_2017 MPG Ranch_Old Bird Redux 1.1_Lilo_Tone.h5
Tseep_2017 MPG Ranch_Old Bird Redux 1.1_MPG North_CHSP-DEJU.h5
Tseep_2017 MPG Ranch_Old Bird Redux 1.1_MPG North_Call.h5
Tseep_2017 MPG Ranch_Old Bird Redux 1.1_MPG North_Noise.h5
Tseep_2017 MPG Ranch_Old Bird Redux 1.1_MPG North_Tone.h5
Tseep_2017 MPG Ranch_Old Bird Redux 1.1_Nelson_CHSP-DEJU.h5
Tseep_2017 MPG Ranch_Old Bird Redux 1.1_Nelson_Call.h5
Tseep_2017 MPG Ranch_Old Bird Redux 1.1_Nelson_Noise.h5
Tseep_2017 MPG Ranch_Old Bird Redux 1.1_Nelson_Tone.h5
Tseep_2017 MPG Ranch_Old Bird Redux 1.1_Oxbow_CHSP-DEJU.h5
Tseep_2017 MPG Ranch_Old Bird Redux 1.1_Oxbow_Call.h5
Tseep_2017 MPG Ranch_Old Bird Redux 1.1_Oxbow_Noise.h5
Tseep_2017 MPG Ranch_Old Bird Redux 1.1_Oxbow_Tone.h5
Tseep_2017 MPG Ranch_Old Bird Redux 1.1_Powell_CHSP-DEJU.h5
Tseep_2017 MPG Ranch_Old Bird Redux 1.1_Powell_Call.h5
Tseep_2017 MPG Ranch_Old Bird Redux 1.1_Powell_Noise.h5
Tseep_2017 MPG Ranch_Old Bird Redux 1.1_Powell_Tone.h5
Tseep_2017 MPG Ranch_Old Bird Redux 1.1_Reed_CHSP-DEJU.h5
Tseep_2017 MPG Ranch_Old Bird Redux 1.1_Reed_Call.h5
Tseep_2017 MPG Ranch_Old Bird Redux 1.1_Reed_Noise.h5
Tseep_2017 MPG Ranch_Old Bird Redux 1.1_Reed_Tone.h5
Tseep_2017 MPG Ranch_Old Bird Redux 1.1_Ridge_CHSP-DEJU.h5
Tseep_2017 MPG Ranch_Old Bird Redux 1.1_Ridge_Call.h5
Tseep_2017 MPG Ranch_Old Bird Redux 1.1_Ridge_Noise.h5
Tseep_2017 MPG Ranch_Old Bird Redux 1.1_Ridge_Tone.h5
Tseep_2017 MPG Ranch_Old Bird Redux 1.1_Seeley_CHSP-DEJU.h5
Tseep_2017 MPG Ranch_Old Bird Redux 1.1_Seeley_Call.h5
Tseep_2017 MPG Ranch_Old Bird Redux 1.1_Seeley_Noise.h5
Tseep_2017 MPG Ranch_Old Bird Redux 1.1_Seeley_Tone.h5
Tseep_2017 MPG Ranch_Old Bird Redux 1.1_Sheep Camp_CHSP-DEJU.h5
Tseep_2017 MPG Ranch_Old Bird Redux 1.1_Sheep Camp_Call.h5
Tseep_2017 MPG Ranch_Old Bird Redux 1.1_Sheep Camp_Noise.h5
Tseep_2017 MPG Ranch_Old Bird Redux 1.1_Sheep Camp_Tone.h5
Tseep_2017 MPG Ranch_Old Bird Redux 1.1_St Mary_CHSP-DEJU.h5
Tseep_2017 MPG Ranch_Old Bird Redux 1.1_St Mary_Call.h5
Tseep_2017 MPG Ranch_Old Bird Redux 1.1_St Mary_Noise.h5
Tseep_2017 MPG Ranch_Old Bird Redux 1.1_St Mary_Tone.h5
Tseep_2017 MPG Ranch_Old Bird Redux 1.1_Sula Peak_CHSP-DEJU.h5
Tseep_2017 MPG Ranch_Old Bird Redux 1.1_Sula Peak_Call.h5
Tseep_2017 MPG Ranch_Old Bird Redux 1.1_Sula Peak_Noise.h5
Tseep_2017 MPG Ranch_Old Bird Redux 1.1_Sula Peak_Tone.h5
Tseep_2017 MPG Ranch_Old Bird Redux 1.1_Teller_CHSP-DEJU.h5
Tseep_2017 MPG Ranch_Old Bird Redux 1.1_Teller_Call.h5
Tseep_2017 MPG Ranch_Old Bird Redux 1.1_Teller_Noise.h5
Tseep_2017 MPG Ranch_Old Bird Redux 1.1_Teller_Tone.h5
Tseep_2017 MPG Ranch_Old Bird Redux 1.1_Troy_CHSP-DEJU.h5
Tseep_2017 MPG Ranch_Old Bird Redux 1.1_Troy_Call.h5
Tseep_2017 MPG Ranch_Old Bird Redux 1.1_Troy_Noise.h5
Tseep_2017 MPG Ranch_Old Bird Redux 1.1_Troy_Tone.h5
Tseep_2017 MPG Ranch_Old Bird Redux 1.1_Walnut_CHSP-DEJU.h5
Tseep_2017 MPG Ranch_Old Bird Redux 1.1_Walnut_Call.h5
Tseep_2017 MPG Ranch_Old Bird Redux 1.1_Walnut_Noise.h5
Tseep_2017 MPG Ranch_Old Bird Redux 1.1_Walnut_Tone.h5
Tseep_2017 MPG Ranch_Old Bird Redux 1.1_Weber_CHSP-DEJU.h5
Tseep_2017 MPG Ranch_Old Bird Redux 1.1_Weber_Call.h5
Tseep_2017 MPG Ranch_Old Bird Redux 1.1_Weber_Noise.h5
Tseep_2017 MPG Ranch_Old Bird Redux 1.1_Weber_Tone.h5
Tseep_2017 MPG Ranch_Old Bird Redux 1.1_Willow_CHSP-DEJU.h5
Tseep_2017 MPG Ranch_Old Bird Redux 1.1_Willow_Call.h5
Tseep_2017 MPG Ranch_Old Bird Redux 1.1_Willow_Noise.h5
Tseep_2017 MPG Ranch_Old Bird Redux 1.1_Willow_Tone.h5
Tseep_2018 MPG Ranch Part 1_Old Bird Redux 1.1_Angel_CHSP-DEJU.h5
Tseep_2018 MPG Ranch Part 1_Old Bird Redux 1.1_Angel_Call.h5
Tseep_2018 MPG Ranch Part 1_Old Bird Redux 1.1_Angel_Noise.h5
Tseep_2018 MPG Ranch Part 1_Old Bird Redux 1.1_Angel_Tone.h5
Tseep_2018 MPG Ranch Part 1_Old Bird Redux 1.1_Bear_CHSP-DEJU.h5
Tseep_2018 MPG Ranch Part 1_Old Bird Redux 1.1_Bear_Call.h5
Tseep_2018 MPG Ranch Part 1_Old Bird Redux 1.1_Bear_Noise.h5
Tseep_2018 MPG Ranch Part 1_Old Bird Redux 1.1_Bear_Tone.h5
Tseep_2018 MPG Ranch Part 1_Old Bird Redux 1.1_Bell Crossing_CHSP-DEJU.h5
Tseep_2018 MPG Ranch Part 1_Old Bird Redux 1.1_Bell Crossing_Call.h5
Tseep_2018 MPG Ranch Part 1_Old Bird Redux 1.1_Bell Crossing_Noise.h5
Tseep_2018 MPG Ranch Part 1_Old Bird Redux 1.1_Bell Crossing_Tone.h5
Tseep_2018 MPG Ranch Part 1_Old Bird Redux 1.1_Bivory_CHSP-DEJU.h5
Tseep_2018 MPG Ranch Part 1_Old Bird Redux 1.1_Bivory_Call.h5
Tseep_2018 MPG Ranch Part 1_Old Bird Redux 1.1_Bivory_Noise.h5
Tseep_2018 MPG Ranch Part 1_Old Bird Redux 1.1_Bivory_Tone.h5
Tseep_2018 MPG Ranch Part 1_Old Bird Redux 1.1_CB Ranch_CHSP-DEJU.h5
Tseep_2018 MPG Ranch Part 1_Old Bird Redux 1.1_CB Ranch_Call.h5
Tseep_2018 MPG Ranch Part 1_Old Bird Redux 1.1_CB Ranch_Noise.h5
Tseep_2018 MPG Ranch Part 1_Old Bird Redux 1.1_CB Ranch_Tone.h5
Tseep_2018 MPG Ranch Part 1_Old Bird Redux 1.1_Coki_CHSP-DEJU.h5
Tseep_2018 MPG Ranch Part 1_Old Bird Redux 1.1_Coki_Call.h5
Tseep_2018 MPG Ranch Part 1_Old Bird Redux 1.1_Coki_Noise.h5
Tseep_2018 MPG Ranch Part 1_Old Bird Redux 1.1_Coki_Tone.h5
Tseep_2018 MPG Ranch Part 1_Old Bird Redux 1.1_Cricket_CHSP-DEJU.h5
Tseep_2018 MPG Ranch Part 1_Old Bird Redux 1.1_Cricket_Call.h5
Tseep_2018 MPG Ranch Part 1_Old Bird Redux 1.1_Cricket_Noise.h5
Tseep_2018 MPG Ranch Part 1_Old Bird Redux 1.1_Cricket_Tone.h5
Tseep_2018 MPG Ranch Part 1_Old Bird Redux 1.1_Darby High School PC_CHSP-DEJU.h5
Tseep_2018 MPG Ranch Part 1_Old Bird Redux 1.1_Darby High School PC_Call.h5
Tseep_2018 MPG Ranch Part 1_Old Bird Redux 1.1_Darby High School PC_Noise.h5
Tseep_2018 MPG Ranch Part 1_Old Bird Redux 1.1_Darby High School PC_Tone.h5
Tseep_2018 MPG Ranch Part 1_Old Bird Redux 1.1_Darby High School Swift_CHSP-DEJU.h5
Tseep_2018 MPG Ranch Part 1_Old Bird Redux 1.1_Darby High School Swift_Call.h5
Tseep_2018 MPG Ranch Part 1_Old Bird Redux 1.1_Darby High School Swift_Noise.h5
Tseep_2018 MPG Ranch Part 1_Old Bird Redux 1.1_Darby High School Swift_Tone.h5
Tseep_2018 MPG Ranch Part 1_Old Bird Redux 1.1_Dashiell_CHSP-DEJU.h5
Tseep_2018 MPG Ranch Part 1_Old Bird Redux 1.1_Dashiell_Call.h5
Tseep_2018 MPG Ranch Part 1_Old Bird Redux 1.1_Dashiell_Noise.h5
Tseep_2018 MPG Ranch Part 1_Old Bird Redux 1.1_Dashiell_Tone.h5
Tseep_2018 MPG Ranch Part 1_Old Bird Redux 1.1_Deer Mountain Lookout_CHSP-DEJU.h5
Tseep_2018 MPG Ranch Part 1_Old Bird Redux 1.1_Deer Mountain Lookout_Call.h5
Tseep_2018 MPG Ranch Part 1_Old Bird Redux 1.1_Deer Mountain Lookout_Noise.h5
Tseep_2018 MPG Ranch Part 1_Old Bird Redux 1.1_Deer Mountain Lookout_Tone.h5
Tseep_2018 MPG Ranch Part 1_Old Bird Redux 1.1_DonnaRae_CHSP-DEJU.h5
Tseep_2018 MPG Ranch Part 1_Old Bird Redux 1.1_DonnaRae_Call.h5
Tseep_2018 MPG Ranch Part 1_Old Bird Redux 1.1_DonnaRae_Noise.h5
Tseep_2018 MPG Ranch Part 1_Old Bird Redux 1.1_DonnaRae_Tone.h5
Tseep_2018 MPG Ranch Part 1_Old Bird Redux 1.1_Dreamcatcher_CHSP-DEJU.h5
Tseep_2018 MPG Ranch Part 1_Old Bird Redux 1.1_Dreamcatcher_Call.h5
Tseep_2018 MPG Ranch Part 1_Old Bird Redux 1.1_Dreamcatcher_Noise.h5
Tseep_2018 MPG Ranch Part 1_Old Bird Redux 1.1_Dreamcatcher_Tone.h5
Tseep_2018 MPG Ranch Part 1_Old Bird Redux 1.1_Esmerelda_CHSP-DEJU.h5
Tseep_2018 MPG Ranch Part 1_Old Bird Redux 1.1_Esmerelda_Call.h5
Tseep_2018 MPG Ranch Part 1_Old Bird Redux 1.1_Esmerelda_Noise.h5
Tseep_2018 MPG Ranch Part 1_Old Bird Redux 1.1_Esmerelda_Tone.h5
Tseep_2018 MPG Ranch Part 1_Old Bird Redux 1.1_Evander_CHSP-DEJU.h5
Tseep_2018 MPG Ranch Part 1_Old Bird Redux 1.1_Evander_Call.h5
Tseep_2018 MPG Ranch Part 1_Old Bird Redux 1.1_Evander_Noise.h5
Tseep_2018 MPG Ranch Part 1_Old Bird Redux 1.1_Evander_Tone.h5
Tseep_2018 MPG Ranch Part 1_Old Bird Redux 1.1_Florence High School_CHSP-DEJU.h5
Tseep_2018 MPG Ranch Part 1_Old Bird Redux 1.1_Florence High School_Call.h5
Tseep_2018 MPG Ranch Part 1_Old Bird Redux 1.1_Florence High School_Noise.h5
Tseep_2018 MPG Ranch Part 1_Old Bird Redux 1.1_Florence High School_Tone.h5
Tseep_2018 MPG Ranch Part 1_Old Bird Redux 1.1_Grandpa's Pond_CHSP-DEJU.h5
Tseep_2018 MPG Ranch Part 1_Old Bird Redux 1.1_Grandpa's Pond_Call.h5
Tseep_2018 MPG Ranch Part 1_Old Bird Redux 1.1_Grandpa's Pond_Noise.h5
Tseep_2018 MPG Ranch Part 1_Old Bird Redux 1.1_Grandpa's Pond_Tone.h5
Tseep_2018 MPG Ranch Part 1_Old Bird Redux 1.1_Heron Crossing_CHSP-DEJU.h5
Tseep_2018 MPG Ranch Part 1_Old Bird Redux 1.1_Heron Crossing_Call.h5
Tseep_2018 MPG Ranch Part 1_Old Bird Redux 1.1_Heron Crossing_Noise.h5
Tseep_2018 MPG Ranch Part 1_Old Bird Redux 1.1_Heron Crossing_Tone.h5
Tseep_2018 MPG Ranch Part 1_Old Bird Redux 1.1_IBO Lucky Peak_CHSP-DEJU.h5
Tseep_2018 MPG Ranch Part 1_Old Bird Redux 1.1_IBO Lucky Peak_Call.h5
Tseep_2018 MPG Ranch Part 1_Old Bird Redux 1.1_IBO Lucky Peak_Noise.h5
Tseep_2018 MPG Ranch Part 1_Old Bird Redux 1.1_IBO Lucky Peak_Tone.h5
Tseep_2018 MPG Ranch Part 1_Old Bird Redux 1.1_IBO River_CHSP-DEJU.h5
Tseep_2018 MPG Ranch Part 1_Old Bird Redux 1.1_IBO River_Call.h5
Tseep_2018 MPG Ranch Part 1_Old Bird Redux 1.1_IBO River_Noise.h5
Tseep_2018 MPG Ranch Part 1_Old Bird Redux 1.1_IBO River_Tone.h5
Tseep_2018 MPG Ranch Part 1_Old Bird Redux 1.1_JJ_CHSP-DEJU.h5
Tseep_2018 MPG Ranch Part 1_Old Bird Redux 1.1_JJ_Call.h5
Tseep_2018 MPG Ranch Part 1_Old Bird Redux 1.1_JJ_Noise.h5
Tseep_2018 MPG Ranch Part 1_Old Bird Redux 1.1_JJ_Tone.h5
Tseep_2018 MPG Ranch Part 1_Old Bird Redux 1.1_KBK_CHSP-DEJU.h5
Tseep_2018 MPG Ranch Part 1_Old Bird Redux 1.1_KBK_Call.h5
Tseep_2018 MPG Ranch Part 1_Old Bird Redux 1.1_KBK_Noise.h5
Tseep_2018 MPG Ranch Part 1_Old Bird Redux 1.1_KBK_Tone.h5
Tseep_2018 MPG Ranch Part 1_Old Bird Redux 1.1_Kate_CHSP-DEJU.h5
Tseep_2018 MPG Ranch Part 1_Old Bird Redux 1.1_Kate_Call.h5
Tseep_2018 MPG Ranch Part 1_Old Bird Redux 1.1_Kate_Noise.h5
Tseep_2018 MPG Ranch Part 1_Old Bird Redux 1.1_Kate_Tone.h5
Tseep_2018 MPG Ranch Part 1_Old Bird Redux 1.1_Lee Metcalf NWR_CHSP-DEJU.h5
Tseep_2018 MPG Ranch Part 1_Old Bird Redux 1.1_Lee Metcalf NWR_Call.h5
Tseep_2018 MPG Ranch Part 1_Old Bird Redux 1.1_Lee Metcalf NWR_Noise.h5
Tseep_2018 MPG Ranch Part 1_Old Bird Redux 1.1_Lee Metcalf NWR_Tone.h5
Tseep_2018 MPG Ranch Part 1_Old Bird Redux 1.1_Lilo_CHSP-DEJU.h5
Tseep_2018 MPG Ranch Part 1_Old Bird Redux 1.1_Lilo_Call.h5
Tseep_2018 MPG Ranch Part 1_Old Bird Redux 1.1_Lilo_Noise.h5
Tseep_2018 MPG Ranch Part 1_Old Bird Redux 1.1_Lilo_Tone.h5
Tseep_2018 MPG Ranch Part 1_Old Bird Redux 1.1_Lost Trail_CHSP-DEJU.h5
Tseep_2018 MPG Ranch Part 1_Old Bird Redux 1.1_Lost Trail_Call.h5
Tseep_2018 MPG Ranch Part 1_Old Bird Redux 1.1_Lost Trail_Noise.h5
Tseep_2018 MPG Ranch Part 1_Old Bird Redux 1.1_Lost Trail_Tone.h5
Tseep_2018 MPG Ranch Part 1_Old Bird Redux 1.1_MPG North_CHSP-DEJU.h5
Tseep_2018 MPG Ranch Part 1_Old Bird Redux 1.1_MPG North_Call.h5
Tseep_2018 MPG Ranch Part 1_Old Bird Redux 1.1_MPG North_Noise.h5
Tseep_2018 MPG Ranch Part 1_Old Bird Redux 1.1_MPG North_Tone.h5
Tseep_2018 MPG Ranch Part 1_Old Bird Redux 1.1_MPG Ranch Floodplain SM2_CHSP-DEJU.h5
Tseep_2018 MPG Ranch Part 1_Old Bird Redux 1.1_MPG Ranch Floodplain SM2_Call.h5
Tseep_2018 MPG Ranch Part 1_Old Bird Redux 1.1_MPG Ranch Floodplain SM2_Noise.h5
Tseep_2018 MPG Ranch Part 1_Old Bird Redux 1.1_MPG Ranch Floodplain SM2_Tone.h5
Tseep_2018 MPG Ranch Part 1_Old Bird Redux 1.1_MPG Ranch Floodplain Swift_CHSP-DEJU.h5
Tseep_2018 MPG Ranch Part 1_Old Bird Redux 1.1_MPG Ranch Floodplain Swift_Call.h5
Tseep_2018 MPG Ranch Part 1_Old Bird Redux 1.1_MPG Ranch Floodplain Swift_Noise.h5
Tseep_2018 MPG Ranch Part 1_Old Bird Redux 1.1_MPG Ranch Floodplain Swift_Tone.h5
Tseep_2018 MPG Ranch Part 1_Old Bird Redux 1.1_MPG Ranch Ridge_CHSP-DEJU.h5
Tseep_2018 MPG Ranch Part 1_Old Bird Redux 1.1_MPG Ranch Ridge_Call.h5
Tseep_2018 MPG Ranch Part 1_Old Bird Redux 1.1_MPG Ranch Ridge_Noise.h5
Tseep_2018 MPG Ranch Part 1_Old Bird Redux 1.1_MPG Ranch Ridge_Tone.h5
Tseep_2018 MPG Ranch Part 1_Old Bird Redux 1.1_MPG Ranch Sheep Camp_CHSP-DEJU.h5
Tseep_2018 MPG Ranch Part 1_Old Bird Redux 1.1_MPG Ranch Sheep Camp_Call.h5
Tseep_2018 MPG Ranch Part 1_Old Bird Redux 1.1_MPG Ranch Sheep Camp_Noise.h5
Tseep_2018 MPG Ranch Part 1_Old Bird Redux 1.1_MPG Ranch Sheep Camp_Tone.h5
Tseep_2018 MPG Ranch Part 1_Old Bird Redux 1.1_MPG Ranch Subdivision_CHSP-DEJU.h5
Tseep_2018 MPG Ranch Part 1_Old Bird Redux 1.1_MPG Ranch Subdivision_Call.h5
Tseep_2018 MPG Ranch Part 1_Old Bird Redux 1.1_MPG Ranch Subdivision_Noise.h5
Tseep_2018 MPG Ranch Part 1_Old Bird Redux 1.1_MPG Ranch Subdivision_Tone.h5
Tseep_2018 MPG Ranch Part 1_Old Bird Redux 1.1_MPG Ranch Zumwalt Ridge_CHSP-DEJU.h5
Tseep_2018 MPG Ranch Part 1_Old Bird Redux 1.1_MPG Ranch Zumwalt Ridge_Call.h5
Tseep_2018 MPG Ranch Part 1_Old Bird Redux 1.1_MPG Ranch Zumwalt Ridge_Noise.h5
Tseep_2018 MPG Ranch Part 1_Old Bird Redux 1.1_MPG Ranch Zumwalt Ridge_Tone.h5
Tseep_2018 MPG Ranch Part 1_Old Bird Redux 1.1_Max_CHSP-DEJU.h5
Tseep_2018 MPG Ranch Part 1_Old Bird Redux 1.1_Max_Call.h5
Tseep_2018 MPG Ranch Part 1_Old Bird Redux 1.1_Max_Noise.h5
Tseep_2018 MPG Ranch Part 1_Old Bird Redux 1.1_Max_Tone.h5
Tseep_2018 MPG Ranch Part 1_Old Bird Redux 1.1_Meadowlark_CHSP-DEJU.h5
Tseep_2018 MPG Ranch Part 1_Old Bird Redux 1.1_Meadowlark_Call.h5
Tseep_2018 MPG Ranch Part 1_Old Bird Redux 1.1_Meadowlark_Noise.h5
Tseep_2018 MPG Ranch Part 1_Old Bird Redux 1.1_Meadowlark_Tone.h5
Tseep_2018 MPG Ranch Part 1_Old Bird Redux 1.1_Mickey_CHSP-DEJU.h5
Tseep_2018 MPG Ranch Part 1_Old Bird Redux 1.1_Mickey_Call.h5
Tseep_2018 MPG Ranch Part 1_Old Bird Redux 1.1_Mickey_Noise.h5
Tseep_2018 MPG Ranch Part 1_Old Bird Redux 1.1_Mickey_Tone.h5
Tseep_2018 MPG Ranch Part 1_Old Bird Redux 1.1_Mitzi_CHSP-DEJU.h5
Tseep_2018 MPG Ranch Part 1_Old Bird Redux 1.1_Mitzi_Call.h5
Tseep_2018 MPG Ranch Part 1_Old Bird Redux 1.1_Mitzi_Noise.h5
Tseep_2018 MPG Ranch Part 1_Old Bird Redux 1.1_Mitzi_Tone.h5
Tseep_2018 MPG Ranch Part 1_Old Bird Redux 1.1_Molly_CHSP-DEJU.h5
Tseep_2018 MPG Ranch Part 1_Old Bird Redux 1.1_Molly_Call.h5
Tseep_2018 MPG Ranch Part 1_Old Bird Redux 1.1_Molly_Noise.h5
Tseep_2018 MPG Ranch Part 1_Old Bird Redux 1.1_Molly_Tone.h5
Tseep_2018 MPG Ranch Part 1_Old Bird Redux 1.1_Oxbow_CHSP-DEJU.h5
Tseep_2018 MPG Ranch Part 1_Old Bird Redux 1.1_Oxbow_Call.h5
Tseep_2018 MPG Ranch Part 1_Old Bird Redux 1.1_Oxbow_Noise.h5
Tseep_2018 MPG Ranch Part 1_Old Bird Redux 1.1_Oxbow_Tone.h5
Tseep_2018 MPG Ranch Part 1_Old Bird Redux 1.1_Panda_CHSP-DEJU.h5
Tseep_2018 MPG Ranch Part 1_Old Bird Redux 1.1_Panda_Call.h5
Tseep_2018 MPG Ranch Part 1_Old Bird Redux 1.1_Panda_Noise.h5
Tseep_2018 MPG Ranch Part 1_Old Bird Redux 1.1_Panda_Tone.h5
Tseep_2018 MPG Ranch Part 1_Old Bird Redux 1.1_Petey_CHSP-DEJU.h5
Tseep_2018 MPG Ranch Part 1_Old Bird Redux 1.1_Petey_Call.h5
Tseep_2018 MPG Ranch Part 1_Old Bird Redux 1.1_Petey_Noise.h5
Tseep_2018 MPG Ranch Part 1_Old Bird Redux 1.1_Petey_Tone.h5
Tseep_2018 MPG Ranch Part 1_Old Bird Redux 1.1_Pocket Gopher_CHSP-DEJU.h5
Tseep_2018 MPG Ranch Part 1_Old Bird Redux 1.1_Pocket Gopher_Call.h5
Tseep_2018 MPG Ranch Part 1_Old Bird Redux 1.1_Pocket Gopher_Noise.h5
Tseep_2018 MPG Ranch Part 1_Old Bird Redux 1.1_Pocket Gopher_Tone.h5
Tseep_2018 MPG Ranch Part 1_Old Bird Redux 1.1_Sadie-Kate_CHSP-DEJU.h5
Tseep_2018 MPG Ranch Part 1_Old Bird Redux 1.1_Sadie-Kate_Call.h5
Tseep_2018 MPG Ranch Part 1_Old Bird Redux 1.1_Sadie-Kate_Noise.h5
Tseep_2018 MPG Ranch Part 1_Old Bird Redux 1.1_Sadie-Kate_Tone.h5
Tseep_2018 MPG Ranch Part 1_Old Bird Redux 1.1_Sasquatch_CHSP-DEJU.h5
Tseep_2018 MPG Ranch Part 1_Old Bird Redux 1.1_Sasquatch_Call.h5
Tseep_2018 MPG Ranch Part 1_Old Bird Redux 1.1_Sasquatch_Noise.h5
Tseep_2018 MPG Ranch Part 1_Old Bird Redux 1.1_Sasquatch_Tone.h5
Tseep_2018 MPG Ranch Part 1_Old Bird Redux 1.1_Seeley High School_CHSP-DEJU.h5
Tseep_2018 MPG Ranch Part 1_Old Bird Redux 1.1_Seeley High School_Call.h5
Tseep_2018 MPG Ranch Part 1_Old Bird Redux 1.1_Seeley High School_Noise.h5
Tseep_2018 MPG Ranch Part 1_Old Bird Redux 1.1_Seeley High School_Tone.h5
Tseep_2018 MPG Ranch Part 1_Old Bird Redux 1.1_Sleeman_CHSP-DEJU.h5
Tseep_2018 MPG Ranch Part 1_Old Bird Redux 1.1_Sleeman_Call.h5
Tseep_2018 MPG Ranch Part 1_Old Bird Redux 1.1_Sleeman_Noise.h5
Tseep_2018 MPG Ranch Part 1_Old Bird Redux 1.1_Sleeman_Tone.h5
Tseep_2018 MPG Ranch Part 1_Old Bird Redux 1.1_Slocum_CHSP-DEJU.h5
Tseep_2018 MPG Ranch Part 1_Old Bird Redux 1.1_Slocum_Call.h5
Tseep_2018 MPG Ranch Part 1_Old Bird Redux 1.1_Slocum_Noise.h5
Tseep_2018 MPG Ranch Part 1_Old Bird Redux 1.1_Slocum_Tone.h5
Tseep_2018 MPG Ranch Part 1_Old Bird Redux 1.1_St Mary Lookout_CHSP-DEJU.h5
Tseep_2018 MPG Ranch Part 1_Old Bird Redux 1.1_St Mary Lookout_Call.h5
Tseep_2018 MPG Ranch Part 1_Old Bird Redux 1.1_St Mary Lookout_Noise.h5
Tseep_2018 MPG Ranch Part 1_Old Bird Redux 1.1_St Mary Lookout_Tone.h5
Tseep_2018 MPG Ranch Part 1_Old Bird Redux 1.1_Sula Peak Lookout_CHSP-DEJU.h5
Tseep_2018 MPG Ranch Part 1_Old Bird Redux 1.1_Sula Peak Lookout_Call.h5
Tseep_2018 MPG Ranch Part 1_Old Bird Redux 1.1_Sula Peak Lookout_Noise.h5
Tseep_2018 MPG Ranch Part 1_Old Bird Redux 1.1_Sula Peak Lookout_Tone.h5
Tseep_2018 MPG Ranch Part 1_Old Bird Redux 1.1_Sula Ranger Station_CHSP-DEJU.h5
Tseep_2018 MPG Ranch Part 1_Old Bird Redux 1.1_Sula Ranger Station_Call.h5
Tseep_2018 MPG Ranch Part 1_Old Bird Redux 1.1_Sula Ranger Station_Noise.h5
Tseep_2018 MPG Ranch Part 1_Old Bird Redux 1.1_Sula Ranger Station_Tone.h5
Tseep_2018 MPG Ranch Part 1_Old Bird Redux 1.1_Teller_CHSP-DEJU.h5
Tseep_2018 MPG Ranch Part 1_Old Bird Redux 1.1_Teller_Call.h5
Tseep_2018 MPG Ranch Part 1_Old Bird Redux 1.1_Teller_Noise.h5
Tseep_2018 MPG Ranch Part 1_Old Bird Redux 1.1_Teller_Tone.h5
Tseep_2018 MPG Ranch Part 1_Old Bird Redux 1.1_Walnut_CHSP-DEJU.h5
Tseep_2018 MPG Ranch Part 1_Old Bird Redux 1.1_Walnut_Call.h5
Tseep_2018 MPG Ranch Part 1_Old Bird Redux 1.1_Walnut_Noise.h5
Tseep_2018 MPG Ranch Part 1_Old Bird Redux 1.1_Walnut_Tone.h5
Tseep_2018 MPG Ranch Part 1_Old Bird Redux 1.1_Willow Mountain Lookout_CHSP-DEJU.h5
Tseep_2018 MPG Ranch Part 1_Old Bird Redux 1.1_Willow Mountain Lookout_Call.h5
Tseep_2018 MPG Ranch Part 1_Old Bird Redux 1.1_Willow Mountain Lookout_Noise.h5
Tseep_2018 MPG Ranch Part 1_Old Bird Redux 1.1_Willow Mountain Lookout_Tone.h5
Tseep_2018 MPG Ranch Part 1_Old Bird Redux 1.1_YVAS_CHSP-DEJU.h5
Tseep_2018 MPG Ranch Part 1_Old Bird Redux 1.1_YVAS_Call.h5
Tseep_2018 MPG Ranch Part 1_Old Bird Redux 1.1_YVAS_Noise.h5
Tseep_2018 MPG Ranch Part 1_Old Bird Redux 1.1_YVAS_Tone.h5
Tseep_2018 MPG Ranch Part 1_Old Bird Redux 1.1_Zuri_CHSP-DEJU.h5
Tseep_2018 MPG Ranch Part 1_Old Bird Redux 1.1_Zuri_Call.h5
Tseep_2018 MPG Ranch Part 1_Old Bird Redux 1.1_Zuri_Noise.h5
Tseep_2018 MPG Ranch Part 1_Old Bird Redux 1.1_Zuri_Tone.h5
Tseep_2018 MPG Ranch Part 2_Old Bird Redux 1.1_Angel_CHSP-DEJU.h5
Tseep_2018 MPG Ranch Part 2_Old Bird Redux 1.1_Angel_Call.h5
Tseep_2018 MPG Ranch Part 2_Old Bird Redux 1.1_Angel_Noise.h5
Tseep_2018 MPG Ranch Part 2_Old Bird Redux 1.1_Angel_Tone.h5
Tseep_2018 MPG Ranch Part 2_Old Bird Redux 1.1_Bear_CHSP-DEJU.h5
Tseep_2018 MPG Ranch Part 2_Old Bird Redux 1.1_Bear_Call.h5
Tseep_2018 MPG Ranch Part 2_Old Bird Redux 1.1_Bear_Noise.h5
Tseep_2018 MPG Ranch Part 2_Old Bird Redux 1.1_Bear_Tone.h5
Tseep_2018 MPG Ranch Part 2_Old Bird Redux 1.1_Bell Crossing_CHSP-DEJU.h5
Tseep_2018 MPG Ranch Part 2_Old Bird Redux 1.1_Bell Crossing_Call.h5
Tseep_2018 MPG Ranch Part 2_Old Bird Redux 1.1_Bell Crossing_Noise.h5
Tseep_2018 MPG Ranch Part 2_Old Bird Redux 1.1_Bell Crossing_Tone.h5
Tseep_2018 MPG Ranch Part 2_Old Bird Redux 1.1_Bivory_CHSP-DEJU.h5
Tseep_2018 MPG Ranch Part 2_Old Bird Redux 1.1_Bivory_Call.h5
Tseep_2018 MPG Ranch Part 2_Old Bird Redux 1.1_Bivory_Noise.h5
Tseep_2018 MPG Ranch Part 2_Old Bird Redux 1.1_Bivory_Tone.h5
Tseep_2018 MPG Ranch Part 2_Old Bird Redux 1.1_CB Ranch_CHSP-DEJU.h5
Tseep_2018 MPG Ranch Part 2_Old Bird Redux 1.1_CB Ranch_Call.h5
Tseep_2018 MPG Ranch Part 2_Old Bird Redux 1.1_CB Ranch_Noise.h5
Tseep_2018 MPG Ranch Part 2_Old Bird Redux 1.1_CB Ranch_Tone.h5
Tseep_2018 MPG Ranch Part 2_Old Bird Redux 1.1_Coki_CHSP-DEJU.h5
Tseep_2018 MPG Ranch Part 2_Old Bird Redux 1.1_Coki_Call.h5
Tseep_2018 MPG Ranch Part 2_Old Bird Redux 1.1_Coki_Noise.h5
Tseep_2018 MPG Ranch Part 2_Old Bird Redux 1.1_Coki_Tone.h5
Tseep_2018 MPG Ranch Part 2_Old Bird Redux 1.1_Cricket_CHSP-DEJU.h5
Tseep_2018 MPG Ranch Part 2_Old Bird Redux 1.1_Cricket_Call.h5
Tseep_2018 MPG Ranch Part 2_Old Bird Redux 1.1_Cricket_Noise.h5
Tseep_2018 MPG Ranch Part 2_Old Bird Redux 1.1_Cricket_Tone.h5
Tseep_2018 MPG Ranch Part 2_Old Bird Redux 1.1_Darby High School PC_CHSP-DEJU.h5
Tseep_2018 MPG Ranch Part 2_Old Bird Redux 1.1_Darby High School PC_Call.h5
Tseep_2018 MPG Ranch Part 2_Old Bird Redux 1.1_Darby High School PC_Noise.h5
Tseep_2018 MPG Ranch Part 2_Old Bird Redux 1.1_Darby High School PC_Tone.h5
Tseep_2018 MPG Ranch Part 2_Old Bird Redux 1.1_Dashiell_CHSP-DEJU.h5
Tseep_2018 MPG Ranch Part 2_Old Bird Redux 1.1_Dashiell_Call.h5
Tseep_2018 MPG Ranch Part 2_Old Bird Redux 1.1_Dashiell_Noise.h5
Tseep_2018 MPG Ranch Part 2_Old Bird Redux 1.1_Dashiell_Tone.h5
Tseep_2018 MPG Ranch Part 2_Old Bird Redux 1.1_Deer Mountain Lookout_CHSP-DEJU.h5
Tseep_2018 MPG Ranch Part 2_Old Bird Redux 1.1_Deer Mountain Lookout_Call.h5
Tseep_2018 MPG Ranch Part 2_Old Bird Redux 1.1_Deer Mountain Lookout_Noise.h5
Tseep_2018 MPG Ranch Part 2_Old Bird Redux 1.1_Deer Mountain Lookout_Tone.h5
Tseep_2018 MPG Ranch Part 2_Old Bird Redux 1.1_DonnaRae_CHSP-DEJU.h5
Tseep_2018 MPG Ranch Part 2_Old Bird Redux 1.1_DonnaRae_Call.h5
Tseep_2018 MPG Ranch Part 2_Old Bird Redux 1.1_DonnaRae_Noise.h5
Tseep_2018 MPG Ranch Part 2_Old Bird Redux 1.1_DonnaRae_Tone.h5
Tseep_2018 MPG Ranch Part 2_Old Bird Redux 1.1_Dreamcatcher_CHSP-DEJU.h5
Tseep_2018 MPG Ranch Part 2_Old Bird Redux 1.1_Dreamcatcher_Call.h5
Tseep_2018 MPG Ranch Part 2_Old Bird Redux 1.1_Dreamcatcher_Noise.h5
Tseep_2018 MPG Ranch Part 2_Old Bird Redux 1.1_Dreamcatcher_Tone.h5
Tseep_2018 MPG Ranch Part 2_Old Bird Redux 1.1_Esmerelda_CHSP-DEJU.h5
Tseep_2018 MPG Ranch Part 2_Old Bird Redux 1.1_Esmerelda_Call.h5
Tseep_2018 MPG Ranch Part 2_Old Bird Redux 1.1_Esmerelda_Noise.h5
Tseep_2018 MPG Ranch Part 2_Old Bird Redux 1.1_Esmerelda_Tone.h5
Tseep_2018 MPG Ranch Part 2_Old Bird Redux 1.1_Evander_CHSP-DEJU.h5
Tseep_2018 MPG Ranch Part 2_Old Bird Redux 1.1_Evander_Call.h5
Tseep_2018 MPG Ranch Part 2_Old Bird Redux 1.1_Evander_Noise.h5
Tseep_2018 MPG Ranch Part 2_Old Bird Redux 1.1_Evander_Tone.h5
Tseep_2018 MPG Ranch Part 2_Old Bird Redux 1.1_Florence High School_CHSP-DEJU.h5
Tseep_2018 MPG Ranch Part 2_Old Bird Redux 1.1_Florence High School_Call.h5
Tseep_2018 MPG Ranch Part 2_Old Bird Redux 1.1_Florence High School_Noise.h5
Tseep_2018 MPG Ranch Part 2_Old Bird Redux 1.1_Florence High School_Tone.h5
Tseep_2018 MPG Ranch Part 2_Old Bird Redux 1.1_Grandpa's Pond_CHSP-DEJU.h5
Tseep_2018 MPG Ranch Part 2_Old Bird Redux 1.1_Grandpa's Pond_Call.h5
Tseep_2018 MPG Ranch Part 2_Old Bird Redux 1.1_Grandpa's Pond_Noise.h5
Tseep_2018 MPG Ranch Part 2_Old Bird Redux 1.1_Grandpa's Pond_Tone.h5
Tseep_2018 MPG Ranch Part 2_Old Bird Redux 1.1_Heron Crossing_CHSP-DEJU.h5
Tseep_2018 MPG Ranch Part 2_Old Bird Redux 1.1_Heron Crossing_Call.h5
Tseep_2018 MPG Ranch Part 2_Old Bird Redux 1.1_Heron Crossing_Noise.h5
Tseep_2018 MPG Ranch Part 2_Old Bird Redux 1.1_Heron Crossing_Tone.h5
Tseep_2018 MPG Ranch Part 2_Old Bird Redux 1.1_IBO Lucky Peak_CHSP-DEJU.h5
Tseep_2018 MPG Ranch Part 2_Old Bird Redux 1.1_IBO Lucky Peak_Call.h5
Tseep_2018 MPG Ranch Part 2_Old Bird Redux 1.1_IBO Lucky Peak_Noise.h5
Tseep_2018 MPG Ranch Part 2_Old Bird Redux 1.1_IBO Lucky Peak_Tone.h5
Tseep_2018 MPG Ranch Part 2_Old Bird Redux 1.1_IBO River_CHSP-DEJU.h5
Tseep_2018 MPG Ranch Part 2_Old Bird Redux 1.1_IBO River_Call.h5
Tseep_2018 MPG Ranch Part 2_Old Bird Redux 1.1_IBO River_Noise.h5
Tseep_2018 MPG Ranch Part 2_Old Bird Redux 1.1_IBO River_Tone.h5
Tseep_2018 MPG Ranch Part 2_Old Bird Redux 1.1_JJ_CHSP-DEJU.h5
Tseep_2018 MPG Ranch Part 2_Old Bird Redux 1.1_JJ_Call.h5
Tseep_2018 MPG Ranch Part 2_Old Bird Redux 1.1_JJ_Noise.h5
Tseep_2018 MPG Ranch Part 2_Old Bird Redux 1.1_JJ_Tone.h5
Tseep_2018 MPG Ranch Part 2_Old Bird Redux 1.1_KBK_CHSP-DEJU.h5
Tseep_2018 MPG Ranch Part 2_Old Bird Redux 1.1_KBK_Call.h5
Tseep_2018 MPG Ranch Part 2_Old Bird Redux 1.1_KBK_Noise.h5
Tseep_2018 MPG Ranch Part 2_Old Bird Redux 1.1_KBK_Tone.h5
Tseep_2018 MPG Ranch Part 2_Old Bird Redux 1.1_Kate_CHSP-DEJU.h5
Tseep_2018 MPG Ranch Part 2_Old Bird Redux 1.1_Kate_Call.h5
Tseep_2018 MPG Ranch Part 2_Old Bird Redux 1.1_Kate_Noise.h5
Tseep_2018 MPG Ranch Part 2_Old Bird Redux 1.1_Kate_Tone.h5
Tseep_2018 MPG Ranch Part 2_Old Bird Redux 1.1_Lee Metcalf NWR_CHSP-DEJU.h5
Tseep_2018 MPG Ranch Part 2_Old Bird Redux 1.1_Lee Metcalf NWR_Call.h5
Tseep_2018 MPG Ranch Part 2_Old Bird Redux 1.1_Lee Metcalf NWR_Noise.h5
Tseep_2018 MPG Ranch Part 2_Old Bird Redux 1.1_Lee Metcalf NWR_Tone.h5
Tseep_2018 MPG Ranch Part 2_Old Bird Redux 1.1_Lilo_CHSP-DEJU.h5
Tseep_2018 MPG Ranch Part 2_Old Bird Redux 1.1_Lilo_Call.h5
Tseep_2018 MPG Ranch Part 2_Old Bird Redux 1.1_Lilo_Noise.h5
Tseep_2018 MPG Ranch Part 2_Old Bird Redux 1.1_Lilo_Tone.h5
Tseep_2018 MPG Ranch Part 2_Old Bird Redux 1.1_Lost Trail_CHSP-DEJU.h5
Tseep_2018 MPG Ranch Part 2_Old Bird Redux 1.1_Lost Trail_Call.h5
Tseep_2018 MPG Ranch Part 2_Old Bird Redux 1.1_Lost Trail_Noise.h5
Tseep_2018 MPG Ranch Part 2_Old Bird Redux 1.1_Lost Trail_Tone.h5
Tseep_2018 MPG Ranch Part 2_Old Bird Redux 1.1_MPG North_CHSP-DEJU.h5
Tseep_2018 MPG Ranch Part 2_Old Bird Redux 1.1_MPG North_Call.h5
Tseep_2018 MPG Ranch Part 2_Old Bird Redux 1.1_MPG North_Noise.h5
Tseep_2018 MPG Ranch Part 2_Old Bird Redux 1.1_MPG North_Tone.h5
Tseep_2018 MPG Ranch Part 2_Old Bird Redux 1.1_MPG Ranch Floodplain_CHSP-DEJU.h5
Tseep_2018 MPG Ranch Part 2_Old Bird Redux 1.1_MPG Ranch Floodplain_Call.h5
Tseep_2018 MPG Ranch Part 2_Old Bird Redux 1.1_MPG Ranch Floodplain_Noise.h5
Tseep_2018 MPG Ranch Part 2_Old Bird Redux 1.1_MPG Ranch Floodplain_Tone.h5
Tseep_2018 MPG Ranch Part 2_Old Bird Redux 1.1_MPG Ranch Ridge_CHSP-DEJU.h5
Tseep_2018 MPG Ranch Part 2_Old Bird Redux 1.1_MPG Ranch Ridge_Call.h5
Tseep_2018 MPG Ranch Part 2_Old Bird Redux 1.1_MPG Ranch Ridge_Noise.h5
Tseep_2018 MPG Ranch Part 2_Old Bird Redux 1.1_MPG Ranch Ridge_Tone.h5
Tseep_2018 MPG Ranch Part 2_Old Bird Redux 1.1_MPG Ranch Sheep Camp_CHSP-DEJU.h5
Tseep_2018 MPG Ranch Part 2_Old Bird Redux 1.1_MPG Ranch Sheep Camp_Call.h5
Tseep_2018 MPG Ranch Part 2_Old Bird Redux 1.1_MPG Ranch Sheep Camp_Noise.h5
Tseep_2018 MPG Ranch Part 2_Old Bird Redux 1.1_MPG Ranch Sheep Camp_Tone.h5
Tseep_2018 MPG Ranch Part 2_Old Bird Redux 1.1_MPG Ranch Subdivision_CHSP-DEJU.h5
Tseep_2018 MPG Ranch Part 2_Old Bird Redux 1.1_MPG Ranch Subdivision_Call.h5
Tseep_2018 MPG Ranch Part 2_Old Bird Redux 1.1_MPG Ranch Subdivision_Noise.h5
Tseep_2018 MPG Ranch Part 2_Old Bird Redux 1.1_MPG Ranch Subdivision_Tone.h5
Tseep_2018 MPG Ranch Part 2_Old Bird Redux 1.1_MPG Ranch Zumwalt Ridge_CHSP-DEJU.h5
Tseep_2018 MPG Ranch Part 2_Old Bird Redux 1.1_MPG Ranch Zumwalt Ridge_Call.h5
Tseep_2018 MPG Ranch Part 2_Old Bird Redux 1.1_MPG Ranch Zumwalt Ridge_Noise.h5
Tseep_2018 MPG Ranch Part 2_Old Bird Redux 1.1_MPG Ranch Zumwalt Ridge_Tone.h5
Tseep_2018 MPG Ranch Part 2_Old Bird Redux 1.1_Max_CHSP-DEJU.h5
Tseep_2018 MPG Ranch Part 2_Old Bird Redux 1.1_Max_Call.h5
Tseep_2018 MPG Ranch Part 2_Old Bird Redux 1.1_Max_Noise.h5
Tseep_2018 MPG Ranch Part 2_Old Bird Redux 1.1_Max_Tone.h5
Tseep_2018 MPG Ranch Part 2_Old Bird Redux 1.1_Meadowlark_CHSP-DEJU.h5
Tseep_2018 MPG Ranch Part 2_Old Bird Redux 1.1_Meadowlark_Call.h5
Tseep_2018 MPG Ranch Part 2_Old Bird Redux 1.1_Meadowlark_Noise.h5
Tseep_2018 MPG Ranch Part 2_Old Bird Redux 1.1_Meadowlark_Tone.h5
Tseep_2018 MPG Ranch Part 2_Old Bird Redux 1.1_Mickey_CHSP-DEJU.h5
Tseep_2018 MPG Ranch Part 2_Old Bird Redux 1.1_Mickey_Call.h5
Tseep_2018 MPG Ranch Part 2_Old Bird Redux 1.1_Mickey_Noise.h5
Tseep_2018 MPG Ranch Part 2_Old Bird Redux 1.1_Mickey_Tone.h5
Tseep_2018 MPG Ranch Part 2_Old Bird Redux 1.1_Mitzi_CHSP-DEJU.h5
Tseep_2018 MPG Ranch Part 2_Old Bird Redux 1.1_Mitzi_Call.h5
Tseep_2018 MPG Ranch Part 2_Old Bird Redux 1.1_Mitzi_Noise.h5
Tseep_2018 MPG Ranch Part 2_Old Bird Redux 1.1_Mitzi_Tone.h5
Tseep_2018 MPG Ranch Part 2_Old Bird Redux 1.1_Molly_CHSP-DEJU.h5
Tseep_2018 MPG Ranch Part 2_Old Bird Redux 1.1_Molly_Call.h5
Tseep_2018 MPG Ranch Part 2_Old Bird Redux 1.1_Molly_Noise.h5
Tseep_2018 MPG Ranch Part 2_Old Bird Redux 1.1_Molly_Tone.h5
Tseep_2018 MPG Ranch Part 2_Old Bird Redux 1.1_Oxbow_CHSP-DEJU.h5
Tseep_2018 MPG Ranch Part 2_Old Bird Redux 1.1_Oxbow_Call.h5
Tseep_2018 MPG Ranch Part 2_Old Bird Redux 1.1_Oxbow_Noise.h5
Tseep_2018 MPG Ranch Part 2_Old Bird Redux 1.1_Oxbow_Tone.h5
Tseep_2018 MPG Ranch Part 2_Old Bird Redux 1.1_Panda_CHSP-DEJU.h5
Tseep_2018 MPG Ranch Part 2_Old Bird Redux 1.1_Panda_Call.h5
Tseep_2018 MPG Ranch Part 2_Old Bird Redux 1.1_Panda_Noise.h5
Tseep_2018 MPG Ranch Part 2_Old Bird Redux 1.1_Panda_Tone.h5
Tseep_2018 MPG Ranch Part 2_Old Bird Redux 1.1_Petey_CHSP-DEJU.h5
Tseep_2018 MPG Ranch Part 2_Old Bird Redux 1.1_Petey_Call.h5
Tseep_2018 MPG Ranch Part 2_Old Bird Redux 1.1_Petey_Noise.h5
Tseep_2018 MPG Ranch Part 2_Old Bird Redux 1.1_Petey_Tone.h5
Tseep_2018 MPG Ranch Part 2_Old Bird Redux 1.1_Pocket Gopher_CHSP-DEJU.h5
Tseep_2018 MPG Ranch Part 2_Old Bird Redux 1.1_Pocket Gopher_Call.h5
Tseep_2018 MPG Ranch Part 2_Old Bird Redux 1.1_Pocket Gopher_Noise.h5
Tseep_2018 MPG Ranch Part 2_Old Bird Redux 1.1_Pocket Gopher_Tone.h5
Tseep_2018 MPG Ranch Part 2_Old Bird Redux 1.1_Sadie-Kate_CHSP-DEJU.h5
Tseep_2018 MPG Ranch Part 2_Old Bird Redux 1.1_Sadie-Kate_Call.h5
Tseep_2018 MPG Ranch Part 2_Old Bird Redux 1.1_Sadie-Kate_Noise.h5
Tseep_2018 MPG Ranch Part 2_Old Bird Redux 1.1_Sadie-Kate_Tone.h5
Tseep_2018 MPG Ranch Part 2_Old Bird Redux 1.1_Sasquatch_CHSP-DEJU.h5
Tseep_2018 MPG Ranch Part 2_Old Bird Redux 1.1_Sasquatch_Call.h5
Tseep_2018 MPG Ranch Part 2_Old Bird Redux 1.1_Sasquatch_Noise.h5
Tseep_2018 MPG Ranch Part 2_Old Bird Redux 1.1_Sasquatch_Tone.h5
Tseep_2018 MPG Ranch Part 2_Old Bird Redux 1.1_Seeley High School_CHSP-DEJU.h5
Tseep_2018 MPG Ranch Part 2_Old Bird Redux 1.1_Seeley High School_Call.h5
Tseep_2018 MPG Ranch Part 2_Old Bird Redux 1.1_Seeley High School_Noise.h5
Tseep_2018 MPG Ranch Part 2_Old Bird Redux 1.1_Seeley High School_Tone.h5
Tseep_2018 MPG Ranch Part 2_Old Bird Redux 1.1_Sleeman_CHSP-DEJU.h5
Tseep_2018 MPG Ranch Part 2_Old Bird Redux 1.1_Sleeman_Call.h5
Tseep_2018 MPG Ranch Part 2_Old Bird Redux 1.1_Sleeman_Noise.h5
Tseep_2018 MPG Ranch Part 2_Old Bird Redux 1.1_Sleeman_Tone.h5
Tseep_2018 MPG Ranch Part 2_Old Bird Redux 1.1_Slocum_CHSP-DEJU.h5
Tseep_2018 MPG Ranch Part 2_Old Bird Redux 1.1_Slocum_Call.h5
Tseep_2018 MPG Ranch Part 2_Old Bird Redux 1.1_Slocum_Noise.h5
Tseep_2018 MPG Ranch Part 2_Old Bird Redux 1.1_Slocum_Tone.h5
Tseep_2018 MPG Ranch Part 2_Old Bird Redux 1.1_St Mary Lookout_CHSP-DEJU.h5
Tseep_2018 MPG Ranch Part 2_Old Bird Redux 1.1_St Mary Lookout_Call.h5
Tseep_2018 MPG Ranch Part 2_Old Bird Redux 1.1_St Mary Lookout_Noise.h5
Tseep_2018 MPG Ranch Part 2_Old Bird Redux 1.1_St Mary Lookout_Tone.h5
Tseep_2018 MPG Ranch Part 2_Old Bird Redux 1.1_Sula Peak Lookout_CHSP-DEJU.h5
Tseep_2018 MPG Ranch Part 2_Old Bird Redux 1.1_Sula Peak Lookout_Call.h5
Tseep_2018 MPG Ranch Part 2_Old Bird Redux 1.1_Sula Peak Lookout_Noise.h5
Tseep_2018 MPG Ranch Part 2_Old Bird Redux 1.1_Sula Peak Lookout_Tone.h5
Tseep_2018 MPG Ranch Part 2_Old Bird Redux 1.1_Sula Ranger Station_CHSP-DEJU.h5
Tseep_2018 MPG Ranch Part 2_Old Bird Redux 1.1_Sula Ranger Station_Call.h5
Tseep_2018 MPG Ranch Part 2_Old Bird Redux 1.1_Sula Ranger Station_Noise.h5
Tseep_2018 MPG Ranch Part 2_Old Bird Redux 1.1_Sula Ranger Station_Tone.h5
Tseep_2018 MPG Ranch Part 2_Old Bird Redux 1.1_Teller_CHSP-DEJU.h5
Tseep_2018 MPG Ranch Part 2_Old Bird Redux 1.1_Teller_Call.h5
Tseep_2018 MPG Ranch Part 2_Old Bird Redux 1.1_Teller_Noise.h5
Tseep_2018 MPG Ranch Part 2_Old Bird Redux 1.1_Teller_Tone.h5
Tseep_2018 MPG Ranch Part 2_Old Bird Redux 1.1_Walnut_CHSP-DEJU.h5
Tseep_2018 MPG Ranch Part 2_Old Bird Redux 1.1_Walnut_Call.h5
Tseep_2018 MPG Ranch Part 2_Old Bird Redux 1.1_Walnut_Noise.h5
Tseep_2018 MPG Ranch Part 2_Old Bird Redux 1.1_Walnut_Tone.h5
Tseep_2018 MPG Ranch Part 2_Old Bird Redux 1.1_Willow Mountain Lookout_CHSP-DEJU.h5
Tseep_2018 MPG Ranch Part 2_Old Bird Redux 1.1_Willow Mountain Lookout_Call.h5
Tseep_2018 MPG Ranch Part 2_Old Bird Redux 1.1_Willow Mountain Lookout_Noise.h5
Tseep_2018 MPG Ranch Part 2_Old Bird Redux 1.1_Willow Mountain Lookout_Tone.h5
Tseep_2018 MPG Ranch Part 2_Old Bird Redux 1.1_YVAS_CHSP-DEJU.h5
Tseep_2018 MPG Ranch Part 2_Old Bird Redux 1.1_YVAS_Call.h5
Tseep_2018 MPG Ranch Part 2_Old Bird Redux 1.1_YVAS_Noise.h5
Tseep_2018 MPG Ranch Part 2_Old Bird Redux 1.1_YVAS_Tone.h5
Tseep_2018 MPG Ranch Part 2_Old Bird Redux 1.1_Zuri_CHSP-DEJU.h5
Tseep_2018 MPG Ranch Part 2_Old Bird Redux 1.1_Zuri_Call.h5
Tseep_2018 MPG Ranch Part 2_Old Bird Redux 1.1_Zuri_Noise.h5
Tseep_2018 MPG Ranch Part 2_Old Bird Redux 1.1_Zuri_Tone.h5
Tseep_2018-08 MPG Ranch Noises_MPG Ranch 0.0_Angel_Noise.h5
Tseep_2018-08 MPG Ranch Noises_MPG Ranch 0.0_Bear_Noise.h5
Tseep_2018-08 MPG Ranch Noises_MPG Ranch 0.0_Bell Crossing_Noise.h5
Tseep_2018-08 MPG Ranch Noises_MPG Ranch 0.0_Bivory_Noise.h5
Tseep_2018-08 MPG Ranch Noises_MPG Ranch 0.0_CB Ranch_Noise.h5
Tseep_2018-08 MPG Ranch Noises_MPG Ranch 0.0_Coki_Noise.h5
Tseep_2018-08 MPG Ranch Noises_MPG Ranch 0.0_Cricket_Noise.h5
Tseep_2018-08 MPG Ranch Noises_MPG Ranch 0.0_Darby High School PC_Noise.h5
Tseep_2018-08 MPG Ranch Noises_MPG Ranch 0.0_Darby High School Swift_Noise.h5
Tseep_2018-08 MPG Ranch Noises_MPG Ranch 0.0_Dashiell_Noise.h5
Tseep_2018-08 MPG Ranch Noises_MPG Ranch 0.0_Deer Mountain Lookout_Noise.h5
Tseep_2018-08 MPG Ranch Noises_MPG Ranch 0.0_DonnaRae_Noise.h5
Tseep_2018-08 MPG Ranch Noises_MPG Ranch 0.0_Dreamcatcher_Noise.h5
Tseep_2018-08 MPG Ranch Noises_MPG Ranch 0.0_Esmerelda_Noise.h5
Tseep_2018-08 MPG Ranch Noises_MPG Ranch 0.0_Evander_Noise.h5
Tseep_2018-08 MPG Ranch Noises_MPG Ranch 0.0_Florence High School_Noise.h5
Tseep_2018-08 MPG Ranch Noises_MPG Ranch 0.0_Grandpa's Pond_Noise.h5
Tseep_2018-08 MPG Ranch Noises_MPG Ranch 0.0_Heron Crossing_Noise.h5
Tseep_2018-08 MPG Ranch Noises_MPG Ranch 0.0_IBO Lucky Peak_Noise.h5
Tseep_2018-08 MPG Ranch Noises_MPG Ranch 0.0_IBO River_Noise.h5
Tseep_2018-08 MPG Ranch Noises_MPG Ranch 0.0_JJ_Noise.h5
Tseep_2018-08 MPG Ranch Noises_MPG Ranch 0.0_KBK_Noise.h5
Tseep_2018-08 MPG Ranch Noises_MPG Ranch 0.0_Kate_Noise.h5
Tseep_2018-08 MPG Ranch Noises_MPG Ranch 0.0_Lee Metcalf NWR_Noise.h5
Tseep_2018-08 MPG Ranch Noises_MPG Ranch 0.0_Lilo_Noise.h5
Tseep_2018-08 MPG Ranch Noises_MPG Ranch 0.0_Lost Trail_Noise.h5
Tseep_2018-08 MPG Ranch Noises_MPG Ranch 0.0_MPG North_Noise.h5
Tseep_2018-08 MPG Ranch Noises_MPG Ranch 0.0_MPG Ranch Floodplain SM2_Noise.h5
Tseep_2018-08 MPG Ranch Noises_MPG Ranch 0.0_MPG Ranch Floodplain Swift_Noise.h5
Tseep_2018-08 MPG Ranch Noises_MPG Ranch 0.0_MPG Ranch Ridge_Noise.h5
Tseep_2018-08 MPG Ranch Noises_MPG Ranch 0.0_MPG Ranch Sheep Camp_Noise.h5
Tseep_2018-08 MPG Ranch Noises_MPG Ranch 0.0_MPG Ranch Subdivision_Noise.h5
Tseep_2018-08 MPG Ranch Noises_MPG Ranch 0.0_MPG Ranch Zumwalt Ridge_Noise.h5
Tseep_2018-08 MPG Ranch Noises_MPG Ranch 0.0_Max_Noise.h5
Tseep_2018-08 MPG Ranch Noises_MPG Ranch 0.0_Meadowlark_Noise.h5
Tseep_2018-08 MPG Ranch Noises_MPG Ranch 0.0_Mickey_Noise.h5
Tseep_2018-08 MPG Ranch Noises_MPG Ranch 0.0_Mitzi_Noise.h5
Tseep_2018-08 MPG Ranch Noises_MPG Ranch 0.0_Molly_Noise.h5
Tseep_2018-08 MPG Ranch Noises_MPG Ranch 0.0_Oxbow_Noise.h5
Tseep_2018-08 MPG Ranch Noises_MPG Ranch 0.0_Panda_Noise.h5
Tseep_2018-08 MPG Ranch Noises_MPG Ranch 0.0_Petey_Noise.h5
Tseep_2018-08 MPG Ranch Noises_MPG Ranch 0.0_Pocket Gopher_Noise.h5
Tseep_2018-08 MPG Ranch Noises_MPG Ranch 0.0_Sadie-Kate_Noise.h5
Tseep_2018-08 MPG Ranch Noises_MPG Ranch 0.0_Sasquatch_Noise.h5
Tseep_2018-08 MPG Ranch Noises_MPG Ranch 0.0_Seeley High School_Noise.h5
Tseep_2018-08 MPG Ranch Noises_MPG Ranch 0.0_Sleeman_Noise.h5
Tseep_2018-08 MPG Ranch Noises_MPG Ranch 0.0_Slocum_Noise.h5
Tseep_2018-08 MPG Ranch Noises_MPG Ranch 0.0_St Mary Lookout_Noise.h5
Tseep_2018-08 MPG Ranch Noises_MPG Ranch 0.0_Sula Peak Lookout_Noise.h5
Tseep_2018-08 MPG Ranch Noises_MPG Ranch 0.0_Sula Ranger Station_Noise.h5
Tseep_2018-08 MPG Ranch Noises_MPG Ranch 0.0_Teller_Noise.h5
Tseep_2018-08 MPG Ranch Noises_MPG Ranch 0.0_Walnut_Noise.h5
Tseep_2018-08 MPG Ranch Noises_MPG Ranch 0.0_Willow Mountain Lookout_Noise.h5
Tseep_2018-08 MPG Ranch Noises_MPG Ranch 0.0_YVAS_Noise.h5
Tseep_2018-08 MPG Ranch Noises_MPG Ranch 0.0_Zuri_Noise.h5
Tseep_2018-09 MPG Ranch Noises_MPG Ranch 0.0_Angel_Noise.h5
Tseep_2018-09 MPG Ranch Noises_MPG Ranch 0.0_Bear_Noise.h5
Tseep_2018-09 MPG Ranch Noises_MPG Ranch 0.0_Bell Crossing_Noise.h5
Tseep_2018-09 MPG Ranch Noises_MPG Ranch 0.0_Bivory_Noise.h5
Tseep_2018-09 MPG Ranch Noises_MPG Ranch 0.0_CB Ranch_Noise.h5
Tseep_2018-09 MPG Ranch Noises_MPG Ranch 0.0_Coki_Noise.h5
Tseep_2018-09 MPG Ranch Noises_MPG Ranch 0.0_Cricket_Noise.h5
Tseep_2018-09 MPG Ranch Noises_MPG Ranch 0.0_Darby High School PC_Noise.h5
Tseep_2018-09 MPG Ranch Noises_MPG Ranch 0.0_Dashiell_Noise.h5
Tseep_2018-09 MPG Ranch Noises_MPG Ranch 0.0_Deer Mountain Lookout_Noise.h5
Tseep_2018-09 MPG Ranch Noises_MPG Ranch 0.0_DonnaRae_Noise.h5
Tseep_2018-09 MPG Ranch Noises_MPG Ranch 0.0_Dreamcatcher_Noise.h5
Tseep_2018-09 MPG Ranch Noises_MPG Ranch 0.0_Esmerelda_Noise.h5
Tseep_2018-09 MPG Ranch Noises_MPG Ranch 0.0_Evander_Noise.h5
Tseep_2018-09 MPG Ranch Noises_MPG Ranch 0.0_Florence High School_Noise.h5
Tseep_2018-09 MPG Ranch Noises_MPG Ranch 0.0_Grandpa's Pond_Noise.h5
Tseep_2018-09 MPG Ranch Noises_MPG Ranch 0.0_Heron Crossing_Noise.h5
Tseep_2018-09 MPG Ranch Noises_MPG Ranch 0.0_IBO Lucky Peak_Noise.h5
Tseep_2018-09 MPG Ranch Noises_MPG Ranch 0.0_IBO River_Noise.h5
Tseep_2018-09 MPG Ranch Noises_MPG Ranch 0.0_JJ_Noise.h5
Tseep_2018-09 MPG Ranch Noises_MPG Ranch 0.0_KBK_Noise.h5
Tseep_2018-09 MPG Ranch Noises_MPG Ranch 0.0_Kate_Noise.h5
Tseep_2018-09 MPG Ranch Noises_MPG Ranch 0.0_Lee Metcalf NWR_Noise.h5
Tseep_2018-09 MPG Ranch Noises_MPG Ranch 0.0_Lilo_Noise.h5
Tseep_2018-09 MPG Ranch Noises_MPG Ranch 0.0_Lost Trail_Noise.h5
Tseep_2018-09 MPG Ranch Noises_MPG Ranch 0.0_MPG North_Noise.h5
Tseep_2018-09 MPG Ranch Noises_MPG Ranch 0.0_MPG Ranch Floodplain_Noise.h5
Tseep_2018-09 MPG Ranch Noises_MPG Ranch 0.0_MPG Ranch Ridge_Noise.h5
Tseep_2018-09 MPG Ranch Noises_MPG Ranch 0.0_MPG Ranch Sheep Camp_Noise.h5
Tseep_2018-09 MPG Ranch Noises_MPG Ranch 0.0_MPG Ranch Subdivision_Noise.h5
Tseep_2018-09 MPG Ranch Noises_MPG Ranch 0.0_MPG Ranch Zumwalt Ridge_Noise.h5
Tseep_2018-09 MPG Ranch Noises_MPG Ranch 0.0_Max_Noise.h5
Tseep_2018-09 MPG Ranch Noises_MPG Ranch 0.0_Meadowlark_Noise.h5
Tseep_2018-09 MPG Ranch Noises_MPG Ranch 0.0_Mickey_Noise.h5
Tseep_2018-09 MPG Ranch Noises_MPG Ranch 0.0_Mitzi_Noise.h5
Tseep_2018-09 MPG Ranch Noises_MPG Ranch 0.0_Molly_Noise.h5
Tseep_2018-09 MPG Ranch Noises_MPG Ranch 0.0_Oxbow_Noise.h5
Tseep_2018-09 MPG Ranch Noises_MPG Ranch 0.0_Panda_Noise.h5
Tseep_2018-09 MPG Ranch Noises_MPG Ranch 0.0_Petey_Noise.h5
Tseep_2018-09 MPG Ranch Noises_MPG Ranch 0.0_Pocket Gopher_Noise.h5
Tseep_2018-09 MPG Ranch Noises_MPG Ranch 0.0_Sadie-Kate_Noise.h5
Tseep_2018-09 MPG Ranch Noises_MPG Ranch 0.0_Sasquatch_Noise.h5
Tseep_2018-09 MPG Ranch Noises_MPG Ranch 0.0_Seeley High School_Noise.h5
Tseep_2018-09 MPG Ranch Noises_MPG Ranch 0.0_Sleeman_Noise.h5
Tseep_2018-09 MPG Ranch Noises_MPG Ranch 0.0_Slocum_Noise.h5
Tseep_2018-09 MPG Ranch Noises_MPG Ranch 0.0_St Mary Lookout_Noise.h5
Tseep_2018-09 MPG Ranch Noises_MPG Ranch 0.0_Sula Peak Lookout_Noise.h5
Tseep_2018-09 MPG Ranch Noises_MPG Ranch 0.0_Sula Ranger Station_Noise.h5
Tseep_2018-09 MPG Ranch Noises_MPG Ranch 0.0_Teller_Noise.h5
Tseep_2018-09 MPG Ranch Noises_MPG Ranch 0.0_Walnut_Noise.h5
Tseep_2018-09 MPG Ranch Noises_MPG Ranch 0.0_Willow Mountain Lookout_Noise.h5
Tseep_2018-09 MPG Ranch Noises_MPG Ranch 0.0_YVAS_Noise.h5
Tseep_2018-09 MPG Ranch Noises_MPG Ranch 0.0_Zuri_Noise.h5
'''.strip().split('\n')

INPUT_FILE_NAMES = {
    'Thrush': THRUSH_INPUT_FILE_NAMES,
    'Tseep': TSEEP_INPUT_FILE_NAMES,
}[CALL_TYPE]

EXAMPLE_START_OFFSET = {
    'Thrush': .1,
    'Tseep': .1,
}[CALL_TYPE]
"""Dataset example start offset, in seconds."""

EXAMPLE_DURATION = {
    'Thrush': .55,
    'Tseep': .4,
}[CALL_TYPE]
"""Dataset example duration, in seconds."""

EXAMPLE_SAMPLE_RATE = 24000

DATASET_CLASSIFICATIONS = (
    ('Call', 'Call'),
    ('Noise', 'Noise'),
    ('CHSP_DEJU', 'Noise'),
    ('Tone', 'Noise'),
)
"""
Mapping from clip classifications in HDF5 files to clip classifications in
datasets.

The mapping is a sequence of pairs instead of a dictionary since the first
element of each pair is (optionally) a classification prefix rather than
an entire classification, and since order can matter.

When the second element of a pair is `None`, clips whose classifications
in HDF5 files start with the first element of the pair are omitted from
the dataset.
"""

CLIP_TYPE_NAMES = ('call', 'noise')
CLIP_TYPE_CALL = 0
CLIP_TYPE_NOISE = 1

OUTPUT_DIR_PATH = DATA_DIR_PATH / 'Datasets' / CALL_TYPE
OUTPUT_FILE_NAME_FORMAT = '{}_{}_{:04d}.tfrecords'
OUTPUT_FILE_SIZE = 10000  # examples


'''
Following are some notes written in the fall of 2018, toward the beginning
of the development of the MPG Ranch version 3.0 coarse classifiers. I've
retained them because I think they are still somewhat relevant. Some tests
conducted after the notes were written showed that while TensorFlow
computes spectrograms slower than Vesper, the slowdown was acceptable,
and that training with on-the-fly spectrogram computation was acceptably
fast. As of this writing (in the summer of 2019), however, I'm less
excited about computing spectrograms with TensorFlow, since that appears
to limit the flexibility of other types of preprocessing (like
spectrogram normalization) that we might want to experiment with, and
since it appears that there might actually be an overall speed
disadvantage to preprocessing on a GPU rather than on the CPU.

Can compute spectrograms with TensorFlow if we wish. Would it be faster
or not? This should be fairly easy to test, I think. Write a test program
to:

1. Generate a sinusoidal test signal, an hour long, say.
2. Compute a spectrogram of it.

Classification pipeline:

1. Get clip waveform at appropriate sample rate.
2. Compute spectrogram.
3. Slice spectrogram.
4. Input spectrogram to neural network.

I think it would be best for detection and classification datasets (i.e.
sets of TFRecord files) to contain audio clips at the appropriate sample
rate rather than spectrograms, and to compute spectrograms in the TensorFlow
graph. Some advantages to this approach:

1. It makes it easier to experiment with various spectrogram settings. If
the dataset contains spectrograms instead of waveforms, we have to generate
a separate dataset for every set of spectrogram settings we want to try.

2. It makes it easier to ensure consistency in spectrogram computation
in training and inference. When the spectrogram computation is part of
the TensorFlow graph, it is automatically the same in training and
inference since they share the graph. When it is not part of the graph,
the spectrogram computation for dataset creation and inference can get
out of sync.

3. If we use TensorFlow for the spectrogram computation, it can happen
on a GPU.

Potential disadvantages of computing spectrograms in the TensorFlow graph:

1. We have to compute spectrograms on the fly during training, recomputing
the same spectrogram each time we see an example, instead of computing a
spectrogram for each example just once when we create the dataset.

2. TensorFlow spectrogram computation may (or may not) be slower than Vesper
spectrogram.

We can look into these potential disadvantages by timing spectrogram
computations and training. If it turns out that TensorFlow spectrograms
are problematically slow, perhaps we can use our spectrogram from within
TensorFlow. 

Tasks:

1. Compare speed of TensorFlow spectrogram to speed of Vesper spectrogram.

2. Create two versions of a modest-sized TFRecords dataset, one containing
waveforms and the other spectrograms. Compare speed of training with waveform
dataset to speed of training with spectrogram dataset.
'''


class StationNightClipFilter:
    
    
    def __init__(self, filtered_station_nights):
        
        self._filtered_station_nights = filtered_station_nights
        self._filtered_clip_counts = defaultdict(int)
        
    
    def filter(self, clip_attrs):
        
        station = clip_attrs['station']
        
        # TODO: Use `datetime.date.fromisoformat` here when we no
        # longer need to support Python 3.6.
        night = clip_attrs['date']
        yyyy, mm, dd = night.split('-')
        night = time_utils.parse_date(yyyy, mm, dd)

        clip_station_night = (station, night)
        
        result = clip_station_night not in self._filtered_station_nights
        
        if result is False:
            self._filtered_clip_counts[clip_station_night] += 1
 
        return result
    
    def show_filtered_clip_counts(self):
        
        station_nights = sorted(self._filtered_clip_counts.keys())
        
        print('Filtered clip counts:')
        for station_night in station_nights:
            count = self._filtered_clip_counts[station_night]
            print('    {} {}'.format(station_night, count))
                         
    
def main():
    
    # show_number_of_open_files_limits()
    
    create_datasets(DATASET_NAME_PREFIX)
      
    # test_get_dataset_clips()
    
    
def show_number_of_open_files_limits():
    soft, hard = resource.getrlimit(resource.RLIMIT_NOFILE)
    print(
        'Soft and hard number of open file limits are {} and {}.'.format(
            soft, hard))


def create_datasets(dataset_name_prefix):
    
    # Get dataset configutation.
    configs = [Bunch(**c) for c in DATASET_CONFIGS]
    configs = dict((c.dataset_name_prefix, c) for c in configs)
    config = configs[dataset_name_prefix]
      
    inputs = get_inputs()
    
    print('Reading clip metadata from input files...')
    calls, noises = get_clip_metadata(inputs)
      
    print('Assigning clips to datasets...')
    datasets = get_dataset_clips(calls, noises, config)
     
    # show_dataset_stats(datasets)
      
    print('Writing clips to output files...')
    create_output_files(inputs, datasets, config)
    
    close_input_files(inputs)
    
    print('Done.')


def get_inputs():
    return [get_input(*p) for p in enumerate(INPUT_FILE_NAMES)]


def get_input(input_num, file_name):
    
    file_path = INPUT_DIR_PATH / file_name
    file_ = h5py.File(file_path, 'r')
    clips_group = file_['clips']
    
    return Bunch(
        num=input_num,
        file_path=file_path,
        file=file_,
        clips_group=clips_group)


def get_clip_metadata(inputs):
    
    from scripts.detector_eval.manual.station_night_sets import \
        NON_TRAINING_STATION_NIGHTS
            
    start_time = time.time()
    
    filter_ = StationNightClipFilter(NON_TRAINING_STATION_NIGHTS)
    
    num_inputs = len(inputs)
    pairs = []
    for input_ in inputs:
        print((
            '    Reading clip metadata from file "{}" (file {} of '
            '{})...').format(input_.file_path, input_.num + 1, num_inputs))
        pair = get_file_clip_metadata(input_, filter_)
        pairs.append(pair)
    
    # show_input_stats(inputs, pairs)
    filter_.show_filtered_clip_counts()
        
    call_lists, noise_lists = zip(*pairs)
    
    calls = list(itertools.chain.from_iterable(call_lists))
    noises = list(itertools.chain.from_iterable(noise_lists))
    
    end_time = time.time()
    delta = end_time - start_time
    num_calls = len(calls)
    num_noises = len(noises)
    num_clips = num_calls + num_noises
    rate = num_clips / delta
    print((
        '    Read metadata for {} clips ({} calls and {} noises) from {} '
        'input files in {:.1f} seconds, a rate of {:.1f} clips per '
        'second.').format(
            num_clips, num_calls, num_noises, len(inputs), delta, rate))
    
    return calls, noises
        
    
def get_file_clip_metadata(input_, filter_):
    
    input_num = input_.num
    
    calls = []
    noises = []
    
    for clip_id, hdf5_dataset in input_.clips_group.items():
        
        if filter_.filter(hdf5_dataset.attrs):
            
            clip = (input_num, clip_id)
            
            hdf5_classification = hdf5_dataset.attrs['classification']
            
            dataset_classification = \
                get_dataset_classification(hdf5_classification)
    
            if dataset_classification == 'Call':
                calls.append(clip)
            
            elif dataset_classification == 'Noise':
                noises.append(clip)
            
    return calls, noises
    
    
def get_dataset_classification(hdf5_classification):
    
    for hdf5_classification_prefix, dataset_classification in \
            DATASET_CLASSIFICATIONS:
        
        if hdf5_classification.startswith(hdf5_classification_prefix):
            return dataset_classification
        
    # If we get here, no prefix of `classification` is included in
    # `DATASET_CLASSIFICATIONS`.
    return None
        
        
def show_input_stats(inputs, pairs):
    print('Input,Calls,Noises')
    for input_, (calls, noises) in zip(inputs, pairs):
        print('"{}",{},{}'.format(input_.file_path, len(calls), len(noises)))


def get_dataset_clips(calls, noises, config):

    train_calls, val_calls, test_calls = \
        get_dataset_clips_aux(calls, config, CLIP_TYPE_CALL)
        
    train_noises, val_noises, test_noises = \
        get_dataset_clips_aux(noises, config, CLIP_TYPE_NOISE)
        
    return Bunch(
        train=Bunch(calls=train_calls, noises=train_noises),
        val=Bunch(calls=val_calls, noises=val_noises),
        test=Bunch(calls=test_calls, noises=test_noises))
        
        
def get_dataset_clips_aux(clips, config, clip_type_index):
    
    # Get training, validation, and test set sizes from configuration.
    train_size = config.train_dataset_size[clip_type_index]
    val_size = config.val_dataset_size[clip_type_index]
    test_size = config.test_dataset_size[clip_type_index]
    
    num_clips_needed = 1 + val_size + test_size
    if num_clips_needed > len(clips):
        raise ValueError((
            'Not enough clips for specified datasets. Needed {} '
            'clips but got only {}.').format(num_clips_needed, len(clips)))
    
    # Shuffle clips in place.
    random.shuffle(clips)
    
    # Divide clips into training, validation, and test segments.
    test_start = -test_size
    val_start = test_start - val_size
    train_clips = clips[:val_start]
    val_clips = clips[val_start:test_start]
    test_clips = clips[test_start:]
    
    num_train_clips = len(train_clips)
    
    if num_train_clips < train_size:
        # have fewer than requested number of training clips
        
        clip_type_name = CLIP_TYPE_NAMES[clip_type_index]
        print((
            'Repeating some or all of {} {} clips as needed to provide '
            '{} training clips...').format(
                num_train_clips, clip_type_name, train_size))
            
        # Repeat clips as needed, shuffling copies.
        n = train_size // num_train_clips
        r = train_size % num_train_clips
        lists = [get_shuffled_copy(train_clips) for _ in range(n)]
        lists.append(train_clips[:r])
        train_clips = list(itertools.chain.from_iterable(lists))
        
    elif num_train_clips > train_size:
        # have more than requested number of training clips
        
        # Discard unneeded clips.
        train_clips = train_clips[:train_size]
        
    return train_clips, val_clips, test_clips
        

def get_shuffled_copy(x):
    return random.sample(x, len(x))


def show_dataset_stats(datasets):
    print('Dataset,Calls,Noises')
    show_dataset_stats_aux(datasets.train, 'Training')
    show_dataset_stats_aux(datasets.val, 'Validation')
    show_dataset_stats_aux(datasets.test, 'Test')
    
    
def show_dataset_stats_aux(dataset, name):
    print('{},{},{}'.format(name, len(dataset.calls), len(dataset.noises)))
    
    
def create_output_files(inputs, datasets, config):
    delete_output_directory(config.dataset_name_prefix)
    create_output_files_aux(inputs, datasets.train, 'Training', config)
    create_output_files_aux(inputs, datasets.val, 'Validation', config)
    create_output_files_aux(inputs, datasets.test, 'Test', config)
    
    
def delete_output_directory(dataset_name_prefix):
    dir_path = OUTPUT_DIR_PATH / dataset_name_prefix
    if os.path.exists(dir_path):
        os_utils.delete_directory(str(dir_path))
    
    
def create_output_files_aux(inputs, dataset, dataset_name, config):
    
    start_time = time.time()
    
    clips = dataset.calls + dataset.noises
    random.shuffle(clips)
    
    num_clips = len(clips)
    num_files = int(math.ceil(num_clips / OUTPUT_FILE_SIZE))
    
    clip_num = 0
    file_num = 0
    
    while clip_num != num_clips:
        
        file_path = get_output_file_path(config, dataset_name, file_num)
        
        end_clip_num = min(clip_num + OUTPUT_FILE_SIZE, num_clips)
        file_clips = clips[clip_num:end_clip_num]
        
        print(
            '    Writing {} clips to file "{}" (file {} of {})...'.format(
                len(file_clips), file_path, file_num + 1, num_files))
    
        write_output_file(inputs, file_clips, file_path)
               
        clip_num = end_clip_num
        file_num += 1
        
    end_time = time.time()
    delta = end_time - start_time
    rate = len(clips) / delta
    print((
        '    Wrote {} {} clips to {} files in {:.1f} seconds, a rate of '
        '{:.1f} clips per second.').format(
            len(clips), dataset_name, num_files, delta, rate))
        
        
def close_input_files(inputs):
    for i in inputs:
        i.file.close()
        
        
def get_output_file_path(config, dataset_name, file_num):
    
    prefix = config.dataset_name_prefix
    
    file_name = OUTPUT_FILE_NAME_FORMAT.format(prefix, dataset_name, file_num)
    
    return OUTPUT_DIR_PATH / prefix / dataset_name / file_name


def write_output_file(inputs, file_clips, file_path):
    
    print('        closing and reopening input files...')
    
    # Close and reopen input HDF5 files. I do not understand why this
    # is necessary, but without it the script sometimes quits with no
    # error messages before it completes.
    close_input_files(inputs)
    inputs = get_inputs()
    clip_groups = dict((i.num, i.clips_group) for i in inputs)
    
    print('        creating clip TF examples...')
    
    tf_examples = []
    for input_num, clip_id in file_clips:
        clip_ds = clip_groups[input_num][clip_id]
        tf_example = create_tf_example(clip_ds)
        tf_examples.append(tf_example)
        
    print('        writing TF examples to file...')
    
    os_utils.create_parent_directory(file_path)
    with tf.python_io.TFRecordWriter(str(file_path)) as writer:
        for tf_example in tf_examples:
            writer.write(tf_example.SerializeToString())
            
    print('        done')
     

def create_tf_example(clip_ds):
    
    waveform = clip_ds[:]
    attrs = clip_ds.attrs
    
    sample_rate = attrs['sample_rate']
    
    # Trim waveform.
    start_index = int(round(EXAMPLE_START_OFFSET * sample_rate))
    length = int(round(EXAMPLE_DURATION * sample_rate))
    waveform = waveform[start_index:start_index + length]
    
    # Resample if needed.
    if sample_rate != EXAMPLE_SAMPLE_RATE:
        # waveform = resampy.resample(
        #    waveform, sample_rate, EXAMPLE_SAMPLE_RATE)
        waveform = resampling_utils.resample_to_24000_hz(waveform, sample_rate)
    
    waveform_feature = create_bytes_feature(waveform.tobytes())
    
    classification = attrs['classification']
    label = 1 if classification.startswith('Call') else 0
    label_feature = create_int64_feature(label)
    
    clip_id = attrs['clip_id']
    clip_id_feature = create_int64_feature(clip_id)
    
    features = tf.train.Features(
        feature={
            'waveform': waveform_feature,
            'label': label_feature,
            'clip_id': clip_id_feature
        })
    
    return tf.train.Example(features=features)


def create_bytes_feature(value):
    return tf.train.Feature(bytes_list=tf.train.BytesList(value=[value]))


def create_int64_feature(value):
    return tf.train.Feature(int64_list=tf.train.Int64List(value=[value]))


CREATE_DATASETS_TEST_CASES = [
    Bunch(**case) for case in yaml_utils.load('''

- description: balanced inputs and datasets
  num_calls: 10
  num_noises: 10
  train_dataset_size: [6, 6]
  val_dataset_size: [2, 2]
  test_dataset_size: [2, 2]
  
- description: more noises than calls, two calls repeated in training
  num_calls: 8
  num_noises: 10
  train_dataset_size: [6, 6]
  val_dataset_size: [2, 2]
  test_dataset_size: [2, 2]
  
- description: more calls than noises, two noises repeated in training
  num_calls: 10
  num_noises: 8
  train_dataset_size: [6, 6]
  val_dataset_size: [2, 2]
  test_dataset_size: [2, 2]
  
- description: more noises than calls, calls repeated twice in training
  num_calls: 7
  num_noises: 10
  train_dataset_size: [6, 6]
  val_dataset_size: [2, 2]
  test_dataset_size: [2, 2]

- description: more noises than calls, calls repeat 2.5x in training
  num_calls: 6
  num_noises: 9
  train_dataset_size: [5, 5]
  val_dataset_size: [2, 2]
  test_dataset_size: [2, 2]

- description: unbalanced datasets
  num_calls: 10
  num_noises: 10
  train_dataset_size: [6, 4]
  val_dataset_size: [2, 3]
  test_dataset_size: [2, 3]
  
''')]


def test_get_dataset_clips():
    
    for case in CREATE_DATASETS_TEST_CASES:
        
        calls = create_test_clips(case.num_calls, 'c')
        noises = create_test_clips(case.num_noises, 'n')
        
        datasets = get_dataset_clips(calls, noises, case)
        
        show_test_datasets(case, calls, noises, datasets)


def create_test_clips(num_clips, prefix):
    n0 = num_clips // 2
    n1 = num_clips - n0
    input_nums = ([0] * n0) + ([1] * n1)
    clip_ids = ['{}{}'.format(prefix, i) for i in range(num_clips)]
    return list(zip(input_nums, clip_ids))
        

def show_test_datasets(case, calls, noises, datasets):
    
    print('For test case:')
    print('    description: {}'.format(case.description))
    print('    num_calls: {}'.format(case.num_calls))
    print('    num_noises: {}'.format(case.num_noises))
    print('    train_dataset_size: {}'.format(case.train_dataset_size))
    print('    val_dataset_size: {}'.format(case.val_dataset_size))
    print('    test_dataset_size: {}'.format(case.test_dataset_size))
    
    print()
    
    show_test_clips(calls, 'Calls')
    show_test_clips(noises, 'Noises')
    
    print()
    
    show_test_dataset(datasets.train, 'Training')
    show_test_dataset(datasets.val, 'Validation')
    show_test_dataset(datasets.test, 'Test')


def show_test_clips(clips, name):
    print('{} are: {}'.format(name, clips))
    
    
def show_test_dataset(dataset, name):
    print('{} dataset:'.format(name))
    print('   Calls: {}'.format(dataset.calls))
    print('   Noises: {}'.format(dataset.noises))
    print()
    
    
if __name__ == '__main__':
    main()
