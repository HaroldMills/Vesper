"""
Plots precision vs. recall curves for the Old Bird detectors run on the
BirdVox-full-night recordings.
"""


from collections import defaultdict
import csv

from matplotlib.backends.backend_pdf import PdfPages
from matplotlib.ticker import MultipleLocator
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

import scripts.old_bird_detector_eval.utils as utils


'''

Input columns:
    Call centers: Center Index, Center Frequency
    Old Bird Detections: Detector, Unit, Threshold, Start Index, Length

Output columns:
    Detector, Unit, Threshold, Ground Truth Calls, Old Bird Calls,
        Old Bird Clips, Precision, Recall, F1
    Detector, Unit, Ground Truth Calls, Old Bird Calls,
        Old Bird Clips, Precision, Recall, F1
        
'''


def main():
    
    old_bird_clips = get_old_bird_clips()
    show_old_bird_clip_counts(old_bird_clips)
        
    ground_truth_call_centers = get_ground_truth_call_centers()
    show_ground_truth_call_counts(ground_truth_call_centers)
    
    rows = count_old_bird_calls(old_bird_clips, ground_truth_call_centers)
    
    raw_df = create_raw_df(rows)
    separated_df = create_separated_detectors_df(raw_df)
    merged_df = create_merged_detectors_df(separated_df)
    
    add_precision_recall_f1(raw_df)
    add_precision_recall_f1(separated_df)
    add_precision_recall_f1(merged_df)
    
    print(raw_df.to_csv())
    print(separated_df.to_csv())
    print(merged_df.to_csv())
    
    plot_precision_vs_recall(separated_df, merged_df)
    
    
def get_old_bird_clips():
    
    clips = defaultdict(list)
        
    with open(utils.OLD_BIRD_CLIPS_FILE_PATH) as file_:
        
        reader = csv.reader(file_)
        
        # Skip header.
        next(reader)
        
        for row in reader:
            key = (row[0], int(row[1]), float(row[2]))
            value = (int(row[3]), int(row[4]))
            clips[key].append(value)
            
    return clips


def show_old_bird_clip_counts(clips):
    print('Old Bird clip counts:')
    keys = sorted(clips.keys())
    for key in keys:
        print('   ', key, len(clips[key]))


def get_ground_truth_call_centers():
    
    centers = defaultdict(list)
    
    csv_files_dir_path = utils.BIRDVOX_70K_UNIT_CLIPS_CSV_FILES_DIR_PATH
    
    for file_path in sorted(csv_files_dir_path.iterdir()):
        
        if not file_path.name.endswith('.csv'):
            continue
        
        station_num = int(file_path.name.split()[1])
        
        with open(file_path) as file_:
            
            reader = csv.reader(file_)
            
            # Skip header.
            next(reader)
            
            for row in reader:
                
                index = int(row[0])
                freq = int(row[1])
                
                if freq != 0:
                    # clip is call
                    
                    call_type = get_call_type(freq)
                    
                    key = (call_type, station_num)
                    centers[key].append(index)
                    
    return centers
                    
                    
def get_call_type(freq):
    return 'Tseep' if freq >= utils.FREQ_THRESHOLD else 'Thrush'


def show_ground_truth_call_counts(call_centers):
    print('Ground truth call counts:')
    keys = sorted(call_centers.keys())
    for key in keys:
        print('   ', key, len(call_centers[key]))
    
    
def count_old_bird_calls(old_bird_clips, ground_truth_call_center_indices):
    
    rows = []
    
    for (detector_name, unit_num, threshold), clips in old_bird_clips.items():
        
        call_center_indices = \
            ground_truth_call_center_indices[(detector_name, unit_num)]
        window = utils.OLD_BIRD_CLIP_CALL_CENTER_WINDOWS[detector_name]
        
        matches = utils.match_clips_with_calls(
            clips, call_center_indices, window)
        old_bird_call_count = len(matches)
        
        old_bird_clip_count = len(clips)
        ground_truth_call_count = len(call_center_indices)
        
        rows.append([
            detector_name, unit_num, threshold, ground_truth_call_count,
            old_bird_call_count, old_bird_clip_count])

    return rows


def create_raw_df(rows):
    
    columns = [
        'Detector', 'Unit', 'Threshold', 'Ground Truth Calls',
        'Old Bird Calls', 'Old Bird Clips']
    
    return pd.DataFrame(rows, columns=columns)


def create_separated_detectors_df(df):
    df = df.drop(columns=['Unit'])
    grouped = df.groupby(['Detector', 'Threshold'], as_index=False)
    return grouped.aggregate(np.sum)


def create_merged_detectors_df(df):
    df = df.drop(columns=['Detector'])
    grouped = df.groupby(['Threshold'], as_index=False)
    return grouped.aggregate(np.sum)


def sum_counts(df, detector):
    
    if detector != 'All':
        df = df.loc[df['Detector'] == detector]
    
    return [
        detector,
        df['Ground Truth Calls'].sum(),
        df['Old Bird Calls'].sum(),
        df['Old Bird Clips'].sum()]
    
        
def add_precision_recall_f1(df):
    p = df['Old Bird Calls'] / df['Old Bird Clips']
    r = df['Old Bird Calls'] / df['Ground Truth Calls']
    df['Precision'] = to_percent(p)
    df['Recall'] = to_percent(r)
    df['F1'] = to_percent(2 * p * r / (p + r))


def to_percent(x):
    return round(1000 * x) / 10


def plot_precision_vs_recall(separated_df, merged_df):
    
    with PdfPages('/Users/harold/Desktop/plot.pdf') as pdf:
        
        _, axes = plt.subplots(figsize=(6, 6))
        
        detector_data = {
            ('Tseep', 2, 'C0'),
            ('Thrush', 1.3, 'C1'),
        }
        
        # Plot separate detector curves.
        for detector_name, threshold, color in detector_data:
            
            # Plot curve.
            df = separated_df.loc[separated_df['Detector'] == detector_name]
            precisions = df['Precision'].values
            recalls = df['Recall'].values
            axes.plot(recalls, precisions, color=color, label=detector_name)
            
            # Put marker at Old Bird detector point.
            indices = dict(
                (t, i) for i, t in enumerate(df['Threshold'].values))
            i = indices[threshold]
            axes.plot([recalls[i]], [precisions[i]], marker='o', color=color)
            
        # Plot merged curve.
        precisions = merged_df['Precision'].values
        recalls = merged_df['Recall'].values
        axes.plot(recalls, precisions, color='C2', label='Tseep and Thrush')
        
        plt.xlabel('Recall (%)')
        plt.ylabel('Precision (%)')
        limits = (0, 100)
        plt.xlim(limits)
        plt.ylim(limits)
        major_locator = MultipleLocator(25)
        minor_locator = MultipleLocator(5)
        axes.xaxis.set_major_locator(major_locator)
        axes.xaxis.set_minor_locator(minor_locator)
        axes.yaxis.set_major_locator(major_locator)
        axes.yaxis.set_minor_locator(minor_locator)
        plt.grid(which='both')
        plt.grid(which='minor', alpha=.4)
        axes.legend()
        plt.title('Old Bird Detector Precision vs. Recall')
        
        pdf.savefig()
        
        plt.show()
    
    
if __name__ == '__main__':
    main()
