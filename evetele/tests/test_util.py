import datetime
import unittest
from unittest import mock

import ddt
import pytz

from .. import util


class TestCachedProperty(unittest.TestCase):

    def test_caching(self):

        mock_object = mock.Mock(y=1)

        class A(object):
            species = 'haddock'
            @util.cached_property
            def x(self):
                mock_object.method(fish=self.species)
                return -1
        a = A()

        self.assertTrue(not hasattr(a, A.x.iname))
        self.assertEqual(a.x, -1)
        mock_object.method.assert_called_once_with(fish='haddock')
        self.assertTrue(hasattr(a, A.x.iname))
        a.species = 'cod'
        a.x
        mock_object.method.assert_called_once_with(fish='haddock')


@ddt.ddt
class TestFunctions(unittest.TestCase):

    @ddt.data(
        ['20180702T182837+0000', datetime.date(2018, 7, 2)],
        ['2018-07-02T00:28:37.000+0100', datetime.date(2018, 7, 1)],
        ['2018-07-02T01:28:37.000+0100', datetime.date(2018, 7, 2)],
        ['2018-07-02', datetime.date(2018, 7, 2)]
    )
    @ddt.unpack
    def test_parse_date(self, inp, expected):
        """A (UTC) date object is expected.

        If the input is a timestamp rather than a simple datestamp,
        the date is derived from the UTC datetime.
        """
        self.assertEqual(util.parse_date(inp), expected)

    @ddt.data(
        ['20180702T182837+0000',
         datetime.datetime(2018, 7, 2, 18, 28, 37, tzinfo=pytz.utc)],
        ['2018-07-02T18:28:37.000+0000',
         datetime.datetime(2018, 7, 2, 18, 28, 37, tzinfo=pytz.utc)],
        [datetime.datetime(2018, 7, 2, 18, 28, 37, tzinfo=pytz.utc),
         datetime.datetime(2018, 7, 2, 18, 28, 37, tzinfo=pytz.utc)],
        ['20180702T192837+0100',
         datetime.datetime(2018, 7, 2, 18, 28, 37, tzinfo=pytz.utc)],
    )
    @ddt.unpack
    def test_parse_datetime(self, inp, expected):
        """A UTC datetime object is expected.

        tzinfo is explicitly compared for the actual and expected
        return values of the function.
        """
        actual = util.parse_datetime(inp)
        self.assertEqual(actual, expected)
        self.assertEqual(actual.tzinfo.utcoffset(actual),
                         expected.tzinfo.utcoffset(expected))

    @ddt.data(
        [1530556413000, # milliseconds
         datetime.datetime(2018, 7, 2, 18, 33, 33, tzinfo=pytz.utc)],
        [1530556413,    # seconds
         datetime.datetime(2018, 7, 2, 18, 33, 33, tzinfo=pytz.utc)],
    )
    @ddt.unpack
    def test_parse_epoch_timestamp(self, inp, expected):
        """A UTC datetime object is expected.

        tzinfo is implicitly asserted here by the comparison with test
        data that has it.
        """
        self.assertEqual(util.parse_epoch_timestamp(inp), expected)


if __name__ == '__main__':
    unittest.main()
