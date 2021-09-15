"""
Script that plots a precision-recall curve for a NOGO coarse classifier.
"""


from pathlib import Path
import csv

from matplotlib.backends.backend_pdf import PdfPages
import matplotlib.pyplot as plt
import numpy as np

import vesper.psw.nogo_coarse_classifier_0_0.classifier_utils \
    as classifier_utils
import vesper.psw.nogo_coarse_classifier_0_0.dataset_utils as dataset_utils


CLASSIFIER_DIR_PATH = Path(
    '/Users/harold/Desktop/NFC/Data/Vesper ML/NOGO Coarse Classifier 0.0')

MODEL_TRAINING_NAME = '2021-09-14_17.40.07'

MODEL_EPOCH_NUM = 100

PLOT_FILE_PATH = CLASSIFIER_DIR_PATH / 'Precision-Recall Curve.pdf'

CSV_FILE_PATH = CLASSIFIER_DIR_PATH / 'Precision-Recall Curve.csv'

THRESHOLD_COUNT = 1000


def main():
    
    labels = get_labels()
    predictions = get_predictions()
    
    thresholds = get_thresholds()
    recalls, precisions = \
        compute_recalls_and_precisions(labels, predictions, thresholds)
    
    plot_precision_recall_curve(recalls, precisions)
    write_precision_recall_csv_file(thresholds, recalls, precisions)
           
    
def get_labels():
    dir_path = classifier_utils.get_dataset_dir_path('Validation')
    dataset = \
        dataset_utils.create_waveform_dataset_from_tfrecord_files(dir_path)
    return np.array([float(label) for _, label, _ in dataset])


def get_predictions():
    
    # Get classifier model.
    model = classifier_utils.load_training_model(
        MODEL_TRAINING_NAME, MODEL_EPOCH_NUM)
    
    # Create validation waveform dataset.
    dir_path = classifier_utils.get_dataset_dir_path('Validation')
    waveform_dataset = \
        dataset_utils.create_waveform_dataset_from_tfrecord_files(dir_path)
        
    # Create validation spectrogram dataset.
    training_settings = \
        classifier_utils.load_training_settings(MODEL_TRAINING_NAME)
    inference_settings = \
        classifier_utils.get_inference_settings(training_settings)
    dataset = dataset_utils.create_inference_dataset(
        waveform_dataset, inference_settings)
    
    # Perform inference.
    return model.predict(dataset).flatten()


def get_thresholds():
    return 1 / THRESHOLD_COUNT * np.arange(THRESHOLD_COUNT)
    
   
def compute_recalls_and_precisions(labels, predictions, thresholds):
    
    pairs = [
        compute_recall_and_precision(labels, predictions, t)
        for t in thresholds]
    
    recalls, precisions = list(zip(*pairs))
    
    return recalls, precisions
    
    
def compute_recall_and_precision(labels, predictions, threshold):
    
    label_positive = (labels == 1)
    prediction_positive = (predictions >= threshold)
    
    count = np.count_nonzero
    true_positive_count = count(label_positive & prediction_positive)
    positive_label_count = count(label_positive)
    positive_prediction_count = count(prediction_positive)
    
    recall = true_positive_count / positive_label_count
    precision = true_positive_count / positive_prediction_count
    
    return recall, precision
    

def plot_precision_recall_curve(recalls, precisions):
    
    with PdfPages(PLOT_FILE_PATH) as pdf:
        
        _, axes = plt.subplots()
        
        axes.plot(recalls, precisions)
        axes.set_title('PSW NOGO Classifier 0.0 - Held Out Clips')
        axes.set_xlabel('Recall')
        axes.set_ylabel('Precision')
        axes.set_xlim([0, 1])
        axes.set_ylim([0, 1])
        axes.grid()
        
        pdf.savefig()
        plt.close()
        
        
def write_precision_recall_csv_file(thresholds, recalls, precisions):
    
    triples = zip(thresholds, recalls, precisions)
    
    with open(CSV_FILE_PATH, 'w', newline='') as csv_file:
        writer = csv.writer(csv_file)
        writer.writerow(('Threshold', 'Recall', 'Precision'))
        writer.writerows(triples)
        
        
if __name__ == '__main__':
    main()
