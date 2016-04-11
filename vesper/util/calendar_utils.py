"""Utility functions pertaining to calendars."""


import datetime


def get_year_month_string(year, month):
    date = datetime.date(year, month, 1)
    return datetime.datetime.strftime(date, '%B %Y')
