"""
Evaluates an MPG Ranch coarse classifier, version 3.0.

The script must be run in a directory that contains an archive with only
tseep or thrush clips. The clips must have been classified already by
the coarse classifier to be evaluated, running in evaluation mode. The
script takes a single command line argument, either "Tseep" or "Thrush".

The script creates a precision-recall PDF file and a statistics CSV file
for each station, and overall. It writes the files to the "Tseep" or
"Thrush" subdirectory of `RESULTS_DIR_PATH`. The subdirectory must
already exist.
"""


from pathlib import Path
import sys
import time

from matplotlib.backends.backend_pdf import PdfPages
from matplotlib.ticker import MultipleLocator
import matplotlib.pyplot as plt
import numpy as np

# Set up Django. This must happen before any use of Django, including
# ORM class imports.
import vesper.util.django_utils as django_utils
django_utils.set_up_django()

from vesper.django.app.models import Clip, Station, StringAnnotation
from vesper.util.binary_classification_stats import BinaryClassificationStats


NUM_THRESHOLDS = 101
RESULTS_DIR_PATH = Path(
    '/Users/harold/Desktop/MPG Ranch Coarse Classifier 3.0 Evaluation')
STATS_CSV_FILE_NAME_FORMAT = '{} {} Stats.csv'
PR_PLOT_FILE_NAME_FORMAT = '{} {} PR.pdf'


def main():
    
    # Get classifier name, either "Tseep" or "Thrush".
    classifier_name = sys.argv[1]
    
    thresholds = np.arange(NUM_THRESHOLDS) / float(NUM_THRESHOLDS - 1)
    
    label_arrays = []
    score_arrays = []
    
    for station in Station.objects.all().order_by('name'):
        
        labels, scores = get_station_clip_data(station)
        stats = BinaryClassificationStats(labels, scores, thresholds)
        save_results(classifier_name, station.name, stats)
            
        label_arrays.append(labels)
        score_arrays.append(scores)
        
    labels = np.concatenate(label_arrays)
    scores = np.concatenate(score_arrays)
    
    stats = BinaryClassificationStats(labels, scores, thresholds)
    
    save_results(classifier_name, 'Overall', stats)
    
    
def get_station_clip_data(station):

    print('Processing clips for station "{}"...'.format(station.name))
        
    start_time = time.time()
    
    labels = []
    scores = []
    
    num_clips = 0
     
    for clip in Clip.objects.filter(station_id=station.id):
        
        annotations = get_clip_annotations(clip)
        
        classification = annotations.get('Classification')
        score = annotations.get('Score')
        
        if classification is not None and score is not None:
            
            if classification.startswith('Call') or \
                    classification.startswith('FN'):
                
                label = 1
                
            elif classification == 'Noise' or classification == 'FP':
                label = 0
                
            else:
                label = None
            
            if label is not None:
                labels.append(label)
                scores.append(float(score))
                
        num_clips += 1
    
    elapsed_time = time.time() - start_time
    rate = num_clips / elapsed_time
    print((
        'Processed {} clips for station "{}" in {:.1f} seconds, a rate '
        'of {:.1f} clips per second.').format(
            num_clips, station.name, elapsed_time, rate))
    
    labels = np.array(labels)
    scores = np.array(scores)
    
    return labels, scores
    
    
def get_clip_annotations(clip):
    annotations = list(StringAnnotation.objects.filter(clip_id=clip.id))
    return dict((a.info.name, a.value) for a in annotations)
        
    
def save_results(classifier_name, station_name, stats):
    plot_precision_recall_curve(classifier_name, station_name, stats)
    write_stats_csv_file(classifier_name, station_name, stats)
        
        
def plot_precision_recall_curve(classifier_name, station_name, stats):
    
    file_path = create_results_file_path(
        PR_PLOT_FILE_NAME_FORMAT, classifier_name, station_name)
    
    with PdfPages(file_path) as pdf:
        
        plt.figure(figsize=(6, 6))
        
        # Plot curve.
        plt.plot(stats.recall, stats.precision, 'b')
        
        # Set title, legend, and axis labels.
        plt.title(
            '{} {} Precision vs. Recall'.format(classifier_name, station_name))
        plt.xlabel('Recall')
        plt.ylabel('Precision')
        
        # Set axis limits.
        lower_limit = 0
        plt.xlim((lower_limit, 1))
        plt.ylim((lower_limit, 1))
        
        # Configure grid.
        major_locator = MultipleLocator(.25)
        minor_locator = MultipleLocator(.05)
        axes = plt.gca()
        axes.xaxis.set_major_locator(major_locator)
        axes.xaxis.set_minor_locator(minor_locator)
        axes.yaxis.set_major_locator(major_locator)
        axes.yaxis.set_minor_locator(minor_locator)
        plt.grid(which='both')
        plt.grid(which='minor', alpha=.4)

        pdf.savefig()
        
        plt.close()


def create_results_file_path(file_name_format, classifier_name, station_name):
    file_name = file_name_format.format(classifier_name, station_name)
    return RESULTS_DIR_PATH / classifier_name / file_name


def write_stats_csv_file(classifier_name, station_name, stats):
    
    file_path = create_results_file_path(
        STATS_CSV_FILE_NAME_FORMAT, classifier_name, station_name)
    
    with open(file_path, 'w') as csv_file:
        
        csv_file.write(
            'Threshold,True Positives,False Positives,True Negatives,'
            'False Negatives,Recall,Precision\n')

        s = stats
        
        columns = (
            s.threshold, s.num_true_positives, s.num_false_positives,
            s.num_true_negatives, s.num_false_negatives, s.recall, s.precision)
        
        for t, tp, fp, tn, fn, r, p in zip(*columns):
            csv_file.write(
                '{:.2f},{},{},{},{},{:.3f},{:.3f}\n'.format(
                    t, int(tp), int(fp), int(tn), int(fn), r, p))


if __name__ == '__main__':
    main()
