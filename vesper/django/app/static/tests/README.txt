Jasmine is an open source JavaScript unit testing framework: see
https://github.com/jasmine/jasmine. Jasmine is not part of the Vesper
project, but part of Jasmine is included here to make running Vesper
client unit tests simpler.

To run Vesper's JavaScript unit tests, open a terminal and run the
following commands:

    cd /Users/harold/Documents/Code/Python/Vesper/vesper/django/app
    conda activate vesper-dev
    python -m http.server
    
and then visit the following URL in Chrome:

    http://127.0.0.1:8000/static/tests/vesper-unit-tests.html
    
Edit the vesper-unit-tests.html file if needed to comment out some
tests.
