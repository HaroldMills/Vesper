import subprocess
import time


def _main():
    
    cases = (
        (),
        ('help',),
        ('help', 'help'),
        ('help', 'classify'),
        ('help', 'classify', 'MPG Ranch Outside Clip Classifier'),
        ('help', 'create'),
        ('help', 'detect'),
        ('help', 'detect', 'Old Bird'),
        ('help', 'export'),
        ('help', 'export', 'Call/Noise Segments'),
        ('help', 'export', 'MPG Ranch Clips CSV'),
        ('help', 'import'),
        ('help', 'import', 'MPG Ranch Importer'),
    )
    
    for case in cases:
        _run(case)
    
    
def _run(args):
    args = ('vcl',) + args
    print('Command:', args, '\n')
    subprocess.call(args)
    time.sleep(1)
    print('\n\n')


if __name__ == '__main__':
    _main()
