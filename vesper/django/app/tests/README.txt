This file contains notes about Vesper unit tests, both Django and non-Django.

To make a long story short, I have not found a way to run both Vesper's
Django-specific unit tests (i.e. those of subclasses of
`django.test.TestCase`) and its non-Django-specific unit tests (i.e.
those of subclasses of `unittest.TestCase` but not `django.test.TestCase`)
with one simple command, even though ideally I think

    command activate vesper-latest
    vesper_admin test

should do the trick (for some details about what goes wrong with that,
see below).

I have found, however, that after renaming Vesper's Django-specific unit
test modules so the names start with `dtest_` instead of `test_`, I can run
them alone with:

    cd "Desktop/Test Archive"
    conda activate vesper-latest
    vesper_admin test -p "dtest_*.py" vesper.django

and all of Vesper's other unit tests with:

    cd "/Users/harold/Documents/Code/Python/Vesper/vesper"
    conda activate vesper-latest
    python -m unittest discover -s /Users/harold/Documents/Code/Python/Vesper/vesper

I hope to simplify this at some point, so I can run all of Vesper's unit
tests with a single command, but I've spent enough time on this for now.


Following are some more detailed notes on this issue that might be of use
when I return to it. The notes were made before I renamed Vesper's Django
unit test modules to `dtest_*` from the usual `test_*`. Hopefully I can
eventually restore the original names.

Ideally, I would like to be able to run all Vesper unit tests with something
like:

    command activate vesper-latest
    vesper_admin test

but that currently doesn't work:

* The above, if run from, say, my home directory, complains that it can't
  find a preset directory.
  
* If I `cd` to an archive directory before attempting to run the tests,
  it doesn't find any tests.

* If I try to run tests with `vesper_admin test vesper`, I get a stack
  trace followed by the error message:

  ImportError: 'test_station' module incorrectly imported from
  '/Users/harold/Documents/Code/Python/Vesper/vesper/archive/tests'.
  Expected '/Users/harold/Desktop/Test Archive/vesper/vesper/archive/tests'.
  Is this module globally installed?

From a terminal,

    python -m unittest discover -s /Users/harold/Documents/Code/Python/Vesper/vesper

fails on Django-specific tests and `vesper.signal` tests, unless it is run
from the `vesper` package directory, in which case it still fails on the
Django-specific tests but not on the `vesper.signal` tests.

I can run only the vesper.signal tests from anywhere with:

    python -m unittest discover -s /Users/harold/Documents/Code/Python/Vesper/vesper/signal

I suppose I'm not too surprised that the `unittest` module fails to run
unit tests of `django.test.TestCase` subclasses, since those require some
database scaffolding. It's too bad that I don't seem to be able to use
`vesper_admin test` for both Django-specific and non-Django-specific
unit tests.

I suppose it might work to name Django-specific unit tests with a different
prefix, like `dtest_`, say, instead of `test_` so that they won't be
discovered by `unittest` and can be discovered exclusively (i.e. excluding
non-Django-specific unit tests) by `vesper_admin test`.

I'm not sure why the signal tests are sometimes a problem. Might it have
something to do with the fact that the Python Standard Library has a `signal`
module?

Additional issues:
* `vesper_admin` does not exit after running tests.
* Log messages from preset manager tests.
* Error message about unclosed ephem/data/d3421.bsp after unit tests run.
