import sounddevice as sd


def main():

    print('Host APIs:')
    apis = sd.query_hostapis()
    for api in apis:
        print(api)
    print(sd.default.hostapi)
    print()

    print('Devices:')
    devices = sd.query_devices()
    for device in devices:
        print(device)
    print(sd.default.device)
    print()


if __name__ == '__main__':
    main()
