from pathlib import Path
import csv


_DIR_PATH = Path(
    'Y:/Desktop/NFC/Data/MPG Ranch/'
    'MPG Ranch NFC Coarse Classifier 2.0 Evaluation/2017 MPG Ranch Archive')

_GROUND_TRUTH_FILE_PATH = _DIR_PATH / 'Call Clips Ground Truth.csv'
    
_RECLASSIFIED_FILE_PATH = _DIR_PATH / 'Call Clips Reclassified.csv'


def _main():
    
    gt_thrush_clips, gt_tseep_clips = _read_file(_GROUND_TRUTH_FILE_PATH)
    r_thrush_clips, r_tseep_clips = _read_file(_RECLASSIFIED_FILE_PATH)
    
    _evaluate_classifier('Thrush', gt_thrush_clips, r_thrush_clips)
    _evaluate_classifier('Tseep', gt_tseep_clips, r_tseep_clips)
    
    
def _read_file(path):
    
    thrush_clips = set()
    tseep_clips = set()
    
    clip_sets = {
        5: thrush_clips,
        6: tseep_clips
    }
    
    with open(path) as file_:
        
        reader = csv.reader(file_)
        
        # Skip header.
        next(reader)
        
        for detector_id, clip_id, _ in reader:
            
            detector_id = int(detector_id)
            clip_id = int(clip_id)
            
            clips = clip_sets.get(detector_id)
            
            if clips is not None:
                clips.add(clip_id)
                
    return thrush_clips, tseep_clips


def _evaluate_classifier(clip_type, gt_clips, r_clips):
    num_pos_samples = len(gt_clips)
    num_pos = len(r_clips)
    num_true_pos = len(gt_clips & r_clips)
    recall = num_true_pos / num_pos_samples
    precision = num_true_pos / num_pos
    print('{} recall {:.2f} precision {:.2f}'.format(
        clip_type, recall, precision))
        
    
if __name__ == '__main__':
    _main()
    