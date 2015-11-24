"""Plots NFC coarse classifier training and test results."""


from __future__ import print_function
import os.path
import sys

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd


_DIR_PATH = r'C:\Users\Harold\Desktop\NFC\Data\MPG Ranch'
_CSV_FILE_NAME_SUFFIX = ' Classifier Results.csv'
_PLOT_Y_LIMITS = {
    'Tseep': 10,
    'Thrush': 20
}


def _main():
    
    detector_name = sys.argv[1]
    
    df = _read_csv_file(detector_name)
    df = df.sort(['Training Percent', 'Fold'])
    _add_percent_columns(df)
        
    means_df = df.groupby('Training Percent').aggregate(np.mean)
    
    _plot_results(means_df, detector_name)


def _read_csv_file(detector_name):
    file_name = detector_name + _CSV_FILE_NAME_SUFFIX
    file_path = os.path.join(_DIR_PATH, file_name)
    return pd.read_csv(file_path)


def _add_percent_columns(df):
    _add_percent_columns_aux(df, 'Training Segment')
    _add_percent_columns_aux(df, 'Training Clip')
    _add_percent_columns_aux(df, 'Test Segment')
    _add_percent_columns_aux(df, 'Test Clip')
    
    
def _add_percent_columns_aux(df, prefix):
    _add_percent_columns_aux_1(df, prefix)
    _add_percent_columns_aux_2(df, prefix, 'True Positives', 'False Negatives')
    _add_percent_columns_aux_2(df, prefix, 'False Positives', 'True Negatives')
    
    
def _add_percent_columns_aux_1(df, prefix):
    training_or_test, _ = prefix.split()
    total = df[training_or_test + ' Clips']
    total_correct = \
        df[prefix + ' True Positives'] + df[prefix + ' True Negatives']
    accuracy = 100 * total_correct / total
    df[prefix + ' Accuracy Percent'] = accuracy
    df[prefix + ' Errors Percent'] = 100 - accuracy
        
        
def _add_percent_columns_aux_2(df, prefix, name_a, name_b):
    totals = df[prefix + ' ' + name_a] + df[prefix + ' ' + name_b]
    for name in [name_a, name_b]:
        n = prefix + ' ' + name
        df[n + ' Percent'] = 100 * df[n] / totals
    
    
def _plot_results(df, detector_name):
    
    plt.figure(1, figsize=(7.5, 10))
    
    plt.subplot(211)
    _plot_error_curves(df, detector_name, 'Segment')
    
    plt.subplot(212)
    _plot_error_curves(df, detector_name, 'Clip')
    plt.show()
    
    
def _plot_error_curves(df, detector_name, segment_or_clip):
    
    x = df.index
    
    y = df['Training ' + segment_or_clip + ' Errors Percent']
    plt.plot(x, y, 'g', label='Training Overall')
    y = df['Test ' + segment_or_clip + ' Errors Percent']
    plt.plot(x, y, 'k', label='Test Overall')
    y = df['Test ' + segment_or_clip + ' False Negatives Percent']
    plt.plot(x, y, 'r', label='Test False Negatives')
    y = df['Test ' + segment_or_clip + ' False Positives Percent']
    plt.plot(x, y, 'b', label='Test False Positives')
      
    plt.xlabel('Training Set Size (percent)')
    plt.ylabel('Error Rate (percent)')
    plt.title(detector_name + ' ' + segment_or_clip + ' Classifier')
    plt.ylim([0, _PLOT_Y_LIMITS[detector_name]])
    plt.grid(True)
    plt.legend(prop={'size': 10})
    plt.subplots_adjust(hspace=.4)


if __name__ == '__main__':
    _main()
    