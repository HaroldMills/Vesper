from pathlib import Path
import csv
import sys

from matplotlib.backends.backend_pdf import PdfPages
import matplotlib.pyplot as plt
import numpy as np

from vesper.util.bunch import Bunch
import vesper.mpg_ranch.nfc_species_classifier_2_0.dataset_utils \
    as dataset_utils


DATA_DIR_PATH = Path(
    '/Users/harold/Desktop/NFC/Data/Vesper ML/'
    'MPG Ranch Species Classifier 2.0/Evaluation')

CLIP_COUNTS = [
    1292,    # ATSP
    2121,    # CCSP_BRSP
    45121,   # CHSP
    108552 + 9337,  # Double Up and YRWA
    1726,    # GRSP
    2935,    # LISP
    3551,    # MGWA
    58672,   # SAVS
    10107,   # VESP
    15966,   # WCSP
    45602,   # WIWA
    1823 + 8627     # Zeep and YEWA
]

EXCLUDED_CLASS_NAMES = {
    # 'Double Up',
    # 'VESP',
    # 'WCSP',
    # 'YEWA',
    # 'YRWA',
    # 'Zeep'
}


def main():
    
    model_name = sys.argv[1]
    
    examples = read_examples(model_name)
    
    # show_examples(examples[:10])
    
    plot_accuracies(model_name, examples)
    plot_confusion_matrices(model_name, examples)
        
    
def read_examples(model_name):
    
    example_file_path = DATA_DIR_PATH / f'Examples_{model_name}.csv'
    
    with open(example_file_path) as example_file:
        reader = csv.reader(example_file)
        examples = [parse_example(row) for row in reader]
        
    return examples
        
        
def parse_example(data):
    
    data = [int(d) for d in data]
    
    clip_id = data[0]
    call_start_index = data[1]
    label = data[2]
    scores = np.array(data[3:])
    max_score = np.max(scores)
    max_score_index = np.argmax(scores)
    correct = max_score_index == label
    
    return Bunch(
        clip_id=clip_id,
        call_start_index=call_start_index,
        label=label,
        scores=scores,
        max_score=max_score,
        max_score_index=max_score_index,
        correct=correct)
    
    
def show_examples(examples):
    for e in examples:
        print(
            f'{e.clip_id},{e.call_start_index},{e.label},{e.scores},'
            f'{e.max_score},{e.max_score_index},{e.correct}')
        
        
def plot_accuracies(model_name, examples):
    
    pdf_file_path = DATA_DIR_PATH / f'Accuracies_{model_name}.pdf'

    with PdfPages(pdf_file_path) as pdf:
        
        plot_accuracy(pdf, examples, 'Overall')
        
        for class_name in dataset_utils.CLASS_NAMES:
            filter_ = ClassFilter(class_name)
            class_examples = filter_examples(examples, filter_)
            plot_accuracy(pdf, class_examples, class_name)
    

def plot_accuracy(pdf, examples, name):
    
    example_counts = np.zeros(101, dtype='int')
    correct_counts = np.zeros(101, dtype='int')
    
    for e in examples:
        max_score = e.max_score
        example_counts[max_score] += 1
        if e.correct:
            correct_counts[max_score] += 1
            
    total_example_count = np.sum(example_counts)
    example_counts = accumulate(example_counts)
    correct_counts = accumulate(correct_counts)
            
    # show_accuracy(total_example_count, example_counts, correct_counts)
        
    thresholds = np.arange(101) / 100
    classified_fractions = example_counts / total_example_count
    correct_fractions = correct_counts / np.maximum(example_counts, 1)

    plt.figure()
    plt.plot(thresholds, classified_fractions, label='Fraction Classified')
    plt.plot(thresholds, correct_fractions, label='Fraction Correct')
    plt.xlabel('Threshold')
    plt.xlim([0, 1])
    plt.ylim([0, 1])
    plt.title(f'Tseep Classifier Performance - {name}')
    plt.legend()
    plt.grid()
        
    pdf.savefig()
    
    plt.close()
    
        
def accumulate(x):
    return np.flip(np.cumsum(np.flip(x)))


def show_accuracy(total_example_count, example_counts, correct_counts):
    
    print('Score Threshold,Classified Fraction,Correct Fraction')
    for i in range(101):
        threshold = i / 100
        example_count = example_counts[i]
        correct_count = correct_counts[i]
        classified_fraction = example_count / total_example_count
        correct_fraction = correct_count / max(example_count, 1)
        print(
            f'{threshold:.2f},{classified_fraction:.2f},'
            f'{correct_fraction:.2f}')


class ClassFilter:
    
    def __init__(self, class_name):
        self.class_name = class_name
        
    def __call__(self, example):
        class_name = dataset_utils.CLASS_NAMES[example.label]
        return class_name == self.class_name
    
    
def filter_examples(examples, filter_):
    return [e for e in examples if filter_(e)]


def plot_confusion_matrices(model_name, examples):
    
    pdf_file_path = DATA_DIR_PATH / f'Confusion Matrices_{model_name}.pdf'

    with PdfPages(pdf_file_path) as pdf:
        
        score_thresholds = (60, 70, 80, 90)
        
        for score_threshold in score_thresholds:
            
            filter_ = ScoreFilter(score_threshold)
            filtered_examples = filter_examples(examples, filter_)
            example_fraction = len(filtered_examples) / len(examples)
                
            matrix = get_confusion_matrix(filtered_examples)
            
            overall_accuracy = get_overall_accuracy(matrix)
            
            plot_confusion_matrix(
                pdf, matrix, score_threshold, example_fraction,
                overall_accuracy)


class ScoreFilter:
    
    def __init__(self, score_threshold):
        self.score_threshold = score_threshold
        
    def __call__(self, example):
        class_name = dataset_utils.CLASS_NAMES[example.label]
        excluded = class_name in EXCLUDED_CLASS_NAMES
        return not excluded and example.max_score >= self.score_threshold
    
    
def get_confusion_matrix(examples):
    class_count = dataset_utils.CLASS_COUNT
    matrix = np.zeros((class_count, class_count))
    example_counts = np.zeros(class_count)
    for e in examples:
        matrix[e.label, e.max_score_index] += 1
        example_counts[e.label] += 1
    for class_num in range(class_count):
        example_count = example_counts[class_num]
        if example_count != 0:
            matrix[class_num, :] /= example_count
    return matrix

    
def get_overall_accuracy(matrix):
    
    class_names = dataset_utils.CLASS_NAMES
    
    total_count = 0
    correct_count = 0
    for i, clip_count in enumerate(CLIP_COUNTS):
        if class_names[i] not in EXCLUDED_CLASS_NAMES:
            total_count += clip_count
            correct_count += int(round(matrix[i, i] * clip_count))
        
    return correct_count / total_count
        
        
def plot_confusion_matrix(
        pdf, matrix, score_threshold, example_fraction, overall_accuracy):
        
    # print_confusion_matrix(matrix)
    
    class_count = dataset_utils.CLASS_COUNT
    class_names = dataset_utils.CLASS_NAMES

    plt.figure()
    
    axes = plt.gca()
    axes.imshow(matrix)
    
    ticks = np.arange(class_count)
    axes.set_xticks(ticks)
    axes.set_yticks(ticks)
    
    axes.set_xticklabels(class_names)
    axes.set_yticklabels(class_names)
    
    plt.setp(
        axes.get_xticklabels(), rotation=45, ha='right',
        rotation_mode='anchor')
    
    m = np.array(np.round(100 * matrix), dtype='int')
    for i in range(class_count):
        for j in range(class_count):
            axes.text(j, i, m[i, j], ha='center', va='center', color='w')
            
    score_threshold = int(score_threshold)
    example_percent = int(round(100 * example_fraction))
    overall_accuracy = int(round(100 * overall_accuracy))
    title = (
        f'Tseep Classifier Confusion Matrix - {score_threshold}, '
        f'{example_percent}, {overall_accuracy}')
    axes.set_title(title)
    
    pdf.savefig()
    
    plt.close()

    
def print_confusion_matrix(matrix):
    
    # header
    print('      ', end='')
    for i in range(len(matrix)):
        print_int_matrix_element(i)
    print()
        
    # elements
    for i, row in enumerate(matrix):
        print_int_matrix_element(i)
        for fraction in row:
            print_percent_matrix_element(fraction)
        print()
         
    
def print_int_matrix_element(e):
    print(f'{e:>6d}', end='')


def print_percent_matrix_element(e):
    percent = int(round(100 * e))
    print(f'{percent:>6d}', end='')
    
    
if __name__ == '__main__':
    main()
