"""Module containing class `StatusTable`."""


class StatusTable:

    """
    Information to display in a table in the recorder UI.

    The information includes a title, a sequence of rows (each a tuple of
    cell contents), an optional header, and an optional footer.
    """


    def __init__(self, title, rows, header=None, footer=None):
        self._title = title
        self._rows = rows
        self._header = header
        self._footer = footer


    @property
    def title(self):
        return self._title
    

    @property
    def rows(self):
        return self._rows
    

    @property
    def header(self):
        return self._header
    

    @property
    def footer(self):
        return self._footer
