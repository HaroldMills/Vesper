"""Script that plots NFC coarse classifier learning curves."""


from __future__ import print_function
import os.path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd


_DIR_PATH = r'C:\Users\Harold\Desktop\NFC\Data\MPG Ranch'
_CSV_FILE_PATH = os.path.join(
    _DIR_PATH, 'Tseep Classifier Test Results.csv')


def _main():
    
    df = pd.read_csv(_CSV_FILE_PATH)
    df = df.sort(['Training Percent', 'Fold'])
    _add_percent_columns(df)
        
    means_df = df.groupby('Training Percent').aggregate(np.mean)
    
    _plot_learning_curves(means_df)


def _add_percent_columns(df):
    _add_percent_columns_aux(df, 'Segment')
    _add_percent_columns_aux(df, 'Clip')
    
    
def _add_percent_columns_aux(df, prefix):
    _add_percent_columns_aux_2(df, prefix, 'True Positives', 'False Negatives')
    _add_percent_columns_aux_2(df, prefix, 'False Positives', 'True Negatives')
    
    
def _add_percent_columns_aux_2(df, prefix, name_a, name_b):
    totals = df[prefix + ' ' + name_a] + df[prefix + ' ' + name_b]
    for name in [name_a, name_b]:
        n = prefix + ' ' + name
        df[n + ' Percent'] = 100 * df[n] / totals
    
    
def _plot_learning_curves(df):
    
    plt.subplot(211)
    _plot_learning_curves_aux(df, 'Segment')
    
    plt.subplot(212)
    _plot_learning_curves_aux(df, 'Clip')
    
    plt.show()


def _plot_learning_curves_aux(df, name):
    
    x = df.index
    y = df[name + ' False Negatives Percent']
    plt.plot(x, y, 'b', label='False Negatives')
    y = df[name + ' False Positives Percent']
    plt.plot(x, y, 'g', label='False Positives')
      
    plt.xlabel('Training Set Size (percent)')
    plt.ylabel('Error (percent)')
    plt.title('Tseep ' + name + ' Classifier Learning Curves')
    plt.ylim([0, 10])
    plt.grid(True)
    plt.legend()


if __name__ == '__main__':
    _main()
    