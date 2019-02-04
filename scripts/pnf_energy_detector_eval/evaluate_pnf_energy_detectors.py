"""
Plots precision-recall curves for detectors run on the BirdVox-full-night
recordings.

The inputs required by this script are:

1. CSV files produced by the run_detectors script. The directory containing
the files is specified by
scripts.pnf_energy_detector_eval.utils.WORKING_DIR_PATH. All CSV files in
the directory are processed.

2. The BirdVox-full-night CSV annotation files, as distributed with the
BirdVox-full-night dataset. The directory containing these files is
specified by scripts.pnf_energy_detector_eval.utils.ANNOTATIONS_DIR_PATH.

The outputs produced by this script are:

1. A PDF file for each input CSV file, containing plots of detector
precision-recall curves. The directory to which these files are written
is specified by scripts.pnf_energy_detector_eval.utils.WORKING_DIR_PATH.
"""


from collections import defaultdict
import csv

from matplotlib.backends.backend_pdf import PdfPages
from matplotlib.ticker import MultipleLocator
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

import scripts.pnf_energy_detector_eval.utils as utils


def window(offset, duration):
    s2s = utils.seconds_to_samples
    return (s2s(offset), s2s(duration))


DETECTOR_CALL_CENTER_WINDOWS = {}
"""
Mapping from detector names to clip call center windows. For a
detected clip to be considered a call, its window must contain a
BirdVox-full-night call center.
"""


DEFAULT_DETECTOR_CALL_CENTER_WINDOWS = {
    'Thrush': window(.05, .2),
    'Tseep': window(.05, .2)
}
"""
Mapping from detector types to default clip call center windows,
for detectors for which windows are not specified in
`DETECTOR_CALL_CENTER_WINDOWS`.
"""


DETECTOR_REFERENCE_THRESHOLDS = {
    'Baseline Thrush': 1.3,
    'Baseline Tseep': 2
}
"""
Mapping from detector names to detector reference thresholds.

The plots produced by this script include dots at the reference thresholds.
"""


DEFAULT_DETECTOR_REFERENCE_THRESHOLDS = {
    'Thrush': 2.5,
    'Tseep': 2.7
}
"""
Mapping from detector types to default detector reference thresholds,
for detectors for which reference thresholds are not specified in
`DETECTOR_REFERENCE_THRESHOLDS`.
"""


def main():
    clip_file_paths = sorted(utils.WORKING_DIR_PATH.glob('*.csv'))
    for path in clip_file_paths:
        process_file(path)
    utils.announce('Harold, your evaluation script has finished.')
        
        
def process_file(file_path):
        
    detected_clips = get_detected_clips(file_path)
    show_detected_clip_counts(detected_clips)
        
    ground_truth_call_centers = get_ground_truth_call_centers()
    show_ground_truth_call_counts(ground_truth_call_centers)
    
    counts = count_detected_calls(detected_clips, ground_truth_call_centers)
    
    unaggregated_df = create_unaggregated_df(counts)
    aggregated_df = create_aggregated_df(unaggregated_df)
    
    add_precision_recall_f1(unaggregated_df)
    add_precision_recall_f1(aggregated_df)
    
    print('unaggregated_df', unaggregated_df.to_csv())
    print('aggregated_df', aggregated_df.to_csv())
    
    file_name_base = file_path.name[:-len('.csv')]
    plot_precision_recall_curves(
        file_name_base, unaggregated_df, aggregated_df)
    
    
def get_detected_clips(file_path):
    
    clips = defaultdict(list)
        
    with open(file_path) as file_:
        
        reader = csv.reader(file_)
        
        # Skip header.
        next(reader)
        
        for row in reader:
            key = (row[0], int(row[1]), float(row[2]))
            value = (int(row[3]), int(row[4]))
            clips[key].append(value)
            
    return clips


def show_detected_clip_counts(clips):
    print('Detected clip counts:')
    keys = sorted(clips.keys())
    for key in keys:
        print('   ', key, len(clips[key]))


def get_ground_truth_call_centers():
     
    centers = defaultdict(list)
     
    for unit_num in utils.UNIT_NUMS:
         
        file_path = utils.get_annotations_file_path(unit_num)
         
        with open(file_path) as file_:
             
            reader = csv.reader(file_)
             
            # Skip header.
            next(reader)
             
            for row in reader:
                 
                time = float(row[0])
                index = utils.seconds_to_samples(time)
                 
                freq = int(row[1])
                call_type = get_call_type(freq)
                     
                key = (call_type, unit_num)
                centers[key].append(index)
    
    # Make sure center index lists are sorted.
    for indices in centers.values():
        indices.sort()
        
    return centers
                    
                    
def get_call_type(freq):
    return 'Tseep' if freq >= utils.FREQ_THRESHOLD else 'Thrush'


def show_ground_truth_call_counts(call_centers):
    print('Ground truth call counts:')
    keys = sorted(call_centers.keys())
    for key in keys:
        print('   ', key, len(call_centers[key]))
    
    
def count_detected_calls(detected_clips, ground_truth_call_center_indices):
    
    rows = []
    
    for (detector_name, unit_num, threshold), clips in detected_clips.items():
        
        detector_type = get_detector_type(detector_name)
        
        call_center_indices = \
            ground_truth_call_center_indices[(detector_type, unit_num)]
            
        window = get_detector_call_center_window(detector_name)
        
        if window is None:
            print((
                'Could not find call center window for detector "{}". '
                'Detector will not be evaluated.').format(detector_name))
            continue
        
        matches = match_clips_with_calls(clips, call_center_indices, window)
        detected_call_count = len(matches)
        
        detected_clip_count = len(clips)
        ground_truth_call_count = len(call_center_indices)
        
        rows.append([
            detector_name, unit_num, threshold, ground_truth_call_count,
            detected_call_count, detected_clip_count])

    return rows


def get_detector_type(detector_name):
    return 'Thrush' if detector_name.find('Thrush') != -1 else 'Tseep'


def get_detector_call_center_window(detector_name):
    
    window = DETECTOR_CALL_CENTER_WINDOWS.get(detector_name)
    
    if window is not None:
        return window
        
    else:
        detector_type = get_detector_type(detector_name)
        return DEFAULT_DETECTOR_CALL_CENTER_WINDOWS.get(detector_type)
    
    
def match_clips_with_calls(clips, call_center_indices, window):
    
    clip_windows = [get_clip_window(clip, window) for clip in clips]
    
    clip_count = len(clips)
    call_count = len(call_center_indices)
    
    i = 0
    j = 0
    
    matches = []
    
    while i != clip_count and j != call_count:
        
        window_start_index, window_end_index = clip_windows[i]
        call_center_index = call_center_indices[j]
        
        if window_end_index <= call_center_index:
            # clip window i precedes call center j
            
            i += 1
            
        elif window_start_index > call_center_index:
            # clip window i follows call center j
            
            j += 1
            
        else:
            # clip window i includes call center j
                        
            matches.append((i, j))
            
            i += 1
            j += 1
            
    return matches
            

def get_clip_window(clip, window):
    
    clip_start_index, clip_length = clip
    clip_end_index = clip_start_index + clip_length
    
    window_start_offset, window_length = window
    
    window_start_index = min(
        clip_start_index + window_start_offset, clip_end_index)
        
    window_end_index = min(
        window_start_index + window_length, clip_end_index)
    
    return (window_start_index, window_end_index)

    
def create_unaggregated_df(rows):
    columns = [
        'Detector', 'Unit', 'Threshold', 'Ground Truth Calls',
        'Detected Calls', 'Detected Clips']
    return pd.DataFrame(rows, columns=columns)


def create_aggregated_df(df):
    df = df.drop(columns=['Unit'])
    grouped = df.groupby(['Detector', 'Threshold'], as_index=False)
    return grouped.aggregate(np.sum)


def add_precision_recall_f1(df):
    p = df['Detected Calls'] / df['Detected Clips']
    r = df['Detected Calls'] / df['Ground Truth Calls']
    df['Precision'] = to_percent(p)
    df['Recall'] = to_percent(r)
    df['F1'] = to_percent(2 * p * r / (p + r))


def to_percent(x):
    return round(1000 * x) / 10


def plot_precision_recall_curves(
        file_name_base, unaggregated_df, aggregated_df):
    
    file_path = utils.get_plot_file_path(file_name_base)
    
    with PdfPages(file_path) as pdf:
        
        detector_names = unaggregated_df['Detector'].unique()
        
        plot_precision_recall_curves_aux(
            'All Units', aggregated_df, detector_names, pdf)
        
        for unit_num in utils.UNIT_NUMS:
            unit_name = 'Unit {}'.format(unit_num)
            unit_df = unaggregated_df.loc[unaggregated_df['Unit'] == unit_num]
            if unit_df.shape[0] != 0:
                plot_precision_recall_curves_aux(
                    unit_name, unit_df, detector_names, pdf)
        

def plot_precision_recall_curves_aux(
        title_suffix, full_df, detector_names, pdf):
    
    plt.figure(figsize=(6, 6))
    
    axes = plt.gca()
    
    # Plot separate detector curves.
    for i, detector_name in enumerate(detector_names):
        df = full_df.loc[full_df['Detector'] == detector_name]
        plot_precision_recall_curve(df, detector_name, i, axes)
    
    # Set title and axis labels.
    plt.title('Precision vs. Recall, ' + title_suffix)
    plt.xlabel('Recall (%)')
    plt.ylabel('Precision (%)')
    
    # Set axis limits.
    plt.xlim((0, 100))
    plt.ylim((0, 100))
    
    # Configure grid.
    major_locator = MultipleLocator(25)
    minor_locator = MultipleLocator(5)
    axes.xaxis.set_major_locator(major_locator)
    axes.xaxis.set_minor_locator(minor_locator)
    axes.yaxis.set_major_locator(major_locator)
    axes.yaxis.set_minor_locator(minor_locator)
    plt.grid(which='both')
    plt.grid(which='minor', alpha=.4)
    
    # Show legend.
    axes.legend()
    
    pdf.savefig()
    
    plt.close()
    

def plot_precision_recall_curve(df, detector_name, i, axes):  
    
    color = 'C{}'.format(i)
        
    precisions = df['Precision'].values
    recalls = df['Recall'].values
    label = detector_name
    axes.plot(recalls, precisions, color=color, label=label)
    
    # Put marker at threshold nearest detector reference threshold.
    reference_threshold = get_detector_reference_threshold(detector_name)
    if reference_threshold is not None:
        k = None
        min_diff = 1e6
        for j, t in enumerate(df['Threshold'].values):
            diff = abs(t - reference_threshold)
            if diff < min_diff:
                k = j
                min_diff = diff
        axes.plot([recalls[k]], [precisions[k]], marker='o', color=color)

  
def get_detector_reference_threshold(detector_name):
    
    threshold = DETECTOR_REFERENCE_THRESHOLDS.get(detector_name)
    
    if threshold is not None:
        return threshold
        
    else:
        
        detector_type = get_detector_type(detector_name)
        
        if detector_type is None:
            return None
        
        else:
            return DEFAULT_DETECTOR_REFERENCE_THRESHOLDS.get(detector_type)
    
    
if __name__ == '__main__':
    main()
