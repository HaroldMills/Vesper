"""Plots NFC coarse classifier training and test results."""


from __future__ import print_function
import os.path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd


_DIR_PATH = r'C:\Users\Harold\Desktop\NFC\Data\MPG Ranch'
_CSV_FILE_PATH = os.path.join(_DIR_PATH, 'Tseep Classifier Results.csv')


def _main():
    
    df = pd.read_csv(_CSV_FILE_PATH)
    df = df.sort(['Training Percent', 'Fold'])
    _add_percent_columns(df)
        
    means_df = df.groupby('Training Percent').aggregate(np.mean)
    
    _plot_results(means_df)


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
    
    
def _plot_results(df):
    _plot_error_curves(1, df)
    _plot_detailed_error_curves(2, df, 'Test')
    plt.show()
    
    
def _plot_error_curves(figure_num, df):
    
    _create_figure(figure_num)
    
    plt.subplot(211)
    _plot_error_curves_aux(df, 'Segment')
    
    plt.subplot(212)
    _plot_error_curves_aux(df, 'Clip')
    
    
def _create_figure(figure_num):
    plt.figure(figure_num, figsize=(7.5, 10))


def _plot_error_curves_aux(df, name):
    
    x = df.index
    y = df['Training ' + name + ' Errors Percent']
    plt.plot(x, y, 'r', label='Training')
    y = df['Test ' + name + ' Errors Percent']
    plt.plot(x, y, 'k', label='Test')
    
    plt.xlabel('Training Set Size (percent)')
    plt.ylabel('Error (percent)')
    plt.title('Tseep ' + name + ' Classifier')
    plt.ylim([0, 6])
    plt.grid(True)
    plt.legend()
    
    
def _plot_detailed_error_curves(figure_num, df, name):
    
    _create_figure(figure_num)
    
    plt.subplot(211)
    _plot_detailed_error_curves_aux(df, name, 'Segment')
    
    plt.subplot(212)
    _plot_detailed_error_curves_aux(df, name, 'Clip')


def _plot_detailed_error_curves_aux(df, training_or_test, segment_or_clip):
    
    name = training_or_test + ' ' + segment_or_clip
    
    x = df.index
    y = df[name + ' Errors Percent']
    plt.plot(x, y, 'k', label='Overall')
    y = df[name + ' False Negatives Percent']
    plt.plot(x, y, 'b', label='False Negatives')
    y = df[name + ' False Positives Percent']
    plt.plot(x, y, 'g', label='False Positives')
      
    plt.xlabel('Training Set Size (percent)')
    plt.ylabel(training_or_test + ' Set Error (percent)')
    plt.title('Tseep ' + segment_or_clip + ' Classifier')
    plt.ylim([0, 10])
    plt.grid(True)
    plt.legend()


if __name__ == '__main__':
    _main()
    