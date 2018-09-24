from pathlib import Path
import pickle


JOB_ID = 10000
PICKLE_FILE_PATH = Path('/Users/Harold/Desktop/Job {}.pkl'.format(JOB_ID))
SAMPLE_RATE = 24000
CLIP_PERIOD = 1
CLIP_DURATION = .250
NUM_CLIPS = 10000


def main():
    
    clips = create_clips()
    
    data = {
        'job_id': JOB_ID,
        'clips': clips
    }
    
    with open(PICKLE_FILE_PATH, 'wb') as file_:
        pickle.dump(data, file_)
    
    
def create_clips():
    
    period = int(round(CLIP_PERIOD * SAMPLE_RATE))
    length = int(round(CLIP_DURATION * SAMPLE_RATE))
    
    # (recording_channel_id, start_index, length, creation_time,
    #  creating_processor_id)
    return [
        (102, i * period, length, '2018-09-10 12:00:00', 6)
        for i in range(NUM_CLIPS)]

    
if __name__ == '__main__':
    main()
