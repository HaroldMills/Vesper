This directory contains the file `xtest_archive.py`, which contains unit tests
for the `vesper.django.app.archive.Archive` class, along with a minimal archive
for running the tests. The archive may need to be rebuilt if the tests change.
To rebuild the archive:

    1. Copy file "Archive Database.unpopulated.sqlite" to
       "Archive Database.sqlite".
    2. Set `_POPULATE_DATABASE` to `True` in `test_archive.py`.
    3. Run the unit tests in `test_archive.py`. If they fail, don't worry yet.
    4. Set `_POPULATE_DATABASE` to `False` in `test_archive.py`.
    5. Run the unit tests again. They should succeed. If they don't,
       something needs fixing.

The file "Archive Database.unpopulated.sqlite" is an archive database whose
tables are all empty. It will need to be recreated for new Django versions,
and if the Vesper tables of the database change. Use `vesper_admin migrate`
for that.

For the unit tests of "x_test_archive.py" to work, the root directory
of the PyUnit run must be the test archive directory. Unfortunately,
this means that the tests cannot be run by the "Vesper Unit Tests"
run configuration, since the root directory of that run configuration
is the `vesper` package directory. The tests can be run by the
separate "Vesper x_test_archive.py" run configuration, however. The
module name `x_test_archive` starts with the `x_` prefix to prevent it
from matching the pattern "test_*" specified for the "--include_files"
PyUnit test runner parameter in the PyDev->PyUnit Eclipse Preferences,
i.e. to prevent it from running as part of a "Vesper Unit Tests" run.
