from pathlib import Path
import textwrap


YAML_FILE_PATH = Path('/Users/Harold/Desktop/Clips.yaml')
SAMPLE_RATE = 24000
CLIP_PERIOD = 1
CLIP_DURATION = .250
NUM_CLIPS = 30000


FILE_YAML = '''
clips:

{}
'''.lstrip()


CLIP_YAML = '''
- recording_channel_id: 102
  start_index: {}
  length: {}
  creation_time: "2018-09-10 12:00:00"
  creating_job_id: 100000
  creating_processor_id: 372
'''.lstrip()


def main():
    
    text = create_file_yaml()
    
    with open(YAML_FILE_PATH, 'w') as file_:
        file_.write(text)
    
    
def create_file_yaml():
    
    period = int(round(CLIP_PERIOD * SAMPLE_RATE))
    length = int(round(CLIP_DURATION * SAMPLE_RATE))
    
    # Get list of clip YAMLs.
    clips = [create_clip_yaml(i * period, length) for i in range(NUM_CLIPS)]
    
    # Indent and concatenate.
    clips = '\n'.join(textwrap.indent(c, '    ') for c in clips)
    
    return FILE_YAML.format(clips)


def create_clip_yaml(start_index, length):
    return CLIP_YAML.format(start_index, length)


if __name__ == '__main__':
    main()
