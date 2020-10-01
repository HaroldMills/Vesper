from pathlib import Path
import time

import numpy as np
import tensorflow as tf

import vesper.mpg_ranch.nfc_species_classifier_2_0.classifier_utils \
    as classifier_utils
import vesper.mpg_ranch.nfc_species_classifier_2_0.dataset_utils \
    as dataset_utils


# MODEL_TRAINING_NAME = 'Tseep_2020-09-28_21.10.30'
MODEL_TRAINING_NAME = 'Tseep_2020-09-29_15.50.58'
# MODEL_TRAINING_NAME = 'Tseep_2020-09-30_11.38.15'
MODEL_EPOCH_NUM = '100'
# OUTPUT_FILE_PATH = '/Users/harold/Desktop/classifications.txt'
DATA_DIR_PATH = Path(
    '/Users/harold/Desktop/NFC/Data/Vesper ML/'
    'MPG Ranch Species Classifier 2.0/Evaluation')
OUTPUT_FILE_PATH = DATA_DIR_PATH / f'Examples_{MODEL_TRAINING_NAME}.csv'
EXAMPLE_COUNT = 12000
PROGRESS_MESSAGE_PERIOD = 1000


def main():
    
    tf.compat.v1.enable_eager_execution()
    
    start_time = time.time()
    
    print(f'Classifying {EXAMPLE_COUNT} validation examples...')
    
    model, settings = classifier_utils.load_model_and_settings(
        MODEL_TRAINING_NAME, MODEL_EPOCH_NUM)
    
    dir_path = classifier_utils.get_dataset_dir_path(
        settings.clip_type, 'Validation')
    dataset = dataset_utils.create_spectrogram_dataset(dir_path, settings)
    
    dataset = dataset.take(EXAMPLE_COUNT)
    
    lines = []
    
    for i, example in enumerate(dataset):
        
        if i != 0 and i % PROGRESS_MESSAGE_PERIOD == 0:
            print(f'{i}...')
            
        line = create_file_line(model, *example)
        lines.append(line)
    
    with open(OUTPUT_FILE_PATH, 'w') as file_:
        file_.write('\n'.join(lines) + '\n')
        
    end_time = time.time()
    delta_time = end_time - start_time
    rate = EXAMPLE_COUNT / delta_time
    print(
        f'Processed {EXAMPLE_COUNT} examples in {delta_time:.1f} seconds, '
        f'a rate of {rate:.1f} examples per second.')
    
    
def create_file_line(model, gram, call_start_index, label, _, clip_id):
    
    # Reshape gram for input into Keras CNN.
    gram = tf.expand_dims(gram, 2)
    gram = tf.expand_dims(gram, 0)

    scores = model(gram, training=False)[0].numpy()
    
    clip_id = clip_id.numpy()
    call_start_index = call_start_index.numpy()
    label = label.numpy()
    scores = format_scores(scores)
    
    return f'{clip_id},{call_start_index},{label},{scores}'

    
def get_correct(scores, label):
    if np.argmax(scores) == label:
        return 1
    else:
        return 0
    
    
def format_scores(scores):
    scores = [f'{format_score(scores[i])}' for i in range(len(scores))]
    return ','.join(scores)
    

def format_score(score):
    return str(int(round(100 * score)))


if __name__ == '__main__':
    main()
