from datetime import datetime as DateTime


def main():
    time = DateTime.now()
    print(time)
    print(time.__class__.__name__)
    print(isinstance(time, DateTime))


if __name__ == '__main__':
    main()
