import collections
import datetime
import functools
import logging
import re
import sys

from dateutil import parser
from dateutil.relativedelta import relativedelta as tdelta
import pytz

log = logging.getLogger(__name__)


class cached_property(object):
    # It's probably more sophisticated to use lru_cache or similar a
    # la https://stackoverflow.com/a/33672499/8992969

    def __init__(self, fget):
        self.fget = fget
        self.__doc__ = fget.__doc__
        self.name = name = fget.__name__
        self.iname = '_cached_{}'.format(name)

    def __get__(self, obj, objtype=None):
        if obj is None:
            return self
        try:
            return getattr(obj, self.iname)
        except AttributeError:
            value = self.fget(obj)
            setattr(obj, self.iname, value)
            return value


def exception_logger(cls, inst, traceback):
    # Log any unhandled exception.
    log.exception(': '.join([cls.__name__, str(inst)]))
    sys.__excepthook__(cls, inst, traceback)
sys.excepthook = exception_logger


def get_utc_datetime():
    return datetime.datetime.utcnow().replace(tzinfo=pytz.utc)


def parse_date(obj):
    """Convert a date-like object into a Python date object.


    Parameters
    ----------

    obj : date-like object


    Returns
    -------

    datetime.date


    Notes
    -----

    UTC datetime is used where the object is datetime-like.
    """
    if isinstance(obj, datetime.date):
        # no-op
        return obj
    elif isinstance(obj, str):
        dt = parser.parse(obj)
        dt = dt.replace(tzinfo=dt.tzinfo or pytz.utc) # UTC if naive
        return dt.astimezone(pytz.utc).date()


def parse_datetime(obj):
    """Convert a datetime-like object into a Python UTC datetime.


    Parameters
    ----------

    obj : datetime-like object


    Returns
    -------

    datetime.datetime
    """
    if isinstance(obj, datetime.datetime):
        dt = obj
    else:
        dt = parser.parse(obj)
    return dt.astimezone(pytz.utc)


def parse_epoch_timestamp(timestamp):
    """Convert seconds or milliseconds since epoch to UTC datetime.

    Units will be assumed based on the number of digits in the
    timestamp.


    Parameters
    ----------

    timestamp : int or str
        UNIX timestamp


    Returns
    -------

    datetime.datetime


    Notes
    -----

    This assumes that the timestamp doesn't represent a date before
    2001 (milliseconds have a 13-digit timestamp as far back as 2001).

    Yes, guessing (or rather incorrectly guessing) units is a Bad Idea
    but this is not the Mars Orbiter and luckily the timestamps we are
    dealing with are in a nice, limited range.
    """
    if len(str(timestamp)) >= 13:
        s = int(timestamp) // 1000
        us = int(timestamp) % 1000 * 1000
    else:
        s = int(timestamp)
        us = 0
    converter = datetime.datetime.fromtimestamp
    return converter(s, pytz.UTC).replace(microsecond=us)


def camelcase_to_snakecase(string):
    """Convert a string in camelCase to snake_case."""
    return re.sub(
        r'((?<=[a-z0-9])[A-Z]|(?!^)[A-Z](?=[a-z]))',
        r'_\1',
        string
    ).lower()
