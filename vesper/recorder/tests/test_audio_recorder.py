from vesper.recorder.audio_recorder import AudioRecorder


def main():
    
    devices = AudioRecorder.get_input_devices()
    for device in devices:
        print(device.__dict__)


if __name__ == '__main__':
    main()
