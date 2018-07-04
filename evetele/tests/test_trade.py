import datetime
import functools
import json
import logging
import os
import unittest
from unittest import mock

import pyswagger

from ..trade import MarketOrder
from ..util import parse_datetime, tdelta

from . import DATA_DIR


# Convenience shortcut for mocking properties.
mock_property = functools.partial(
    mock.patch.object,
    new_callable=mock.PropertyMock
)


class TestMarketOrder(unittest.TestCase):
    """Exercise the MarketOrder class.

    The MarketOrder class is a wrapper around market order data,
    exposing those data elements that are used elsewhere in the
    codebase. Data describing Market Orders can come from multiple
    sources in multiple formats and differ slightly in its content and
    purpose, so part of the role of the wrapper is to provide a
    standardised API.

    A MarketOrder is an important, base type this code so some
    flexibility has been built in. Instantiation must always involve
    some data (though it's somewhat trusting about the content!) but
    it can come in the form of a python dict, or a json_string.
    """

    @classmethod
    def setUpClass(cls):
        logging.disable(logging.CRITICAL)

    @classmethod
    def tearDownClass(cls):
        logging.disable(logging.NOTSET)

    def setUp(self):
        self.sut = MarketOrder(data={})

    # ----------------------------------------------------------------
    # Constructors
    # ----------------------------------------------------------------
    def test___init___data(self):
        """Data provided on init is available via the data property.

        The MarketOrder class doesn't actually care what data is
        provided, just that it is a valid dict. Erroneous data will
        become apparent quickly when trying to make use of it and this
        saves testing it.
        """
        data_dict = {'a': 'fish'}
        sut = MarketOrder(data=data_dict)
        self.assertEqual(sut.data, data_dict)

    def test_from_json(self):
        """The JSON constructor provides an alternative init path.

        JSON data is implicitly validated (though the content is not!)
        because the constructor creates the data attribute as a
        side-effect (this is tested here).
        """
        json_string = '{"a": "fish"}'
        sut = MarketOrder.from_json(string=json_string)
        self.assertEqual(sut.data, {'a': 'fish'})

    # ----------------------------------------------------------------
    # Properties
    # ----------------------------------------------------------------
    @mock_property(MarketOrder, 'issued')
    @mock_property(MarketOrder, 'duration')
    def test_expiry(self, stub_duration, stub_issued):
        """Calculated from issue datetime and duration.

        This is not provided in the source data (or in the EVE
        client!) but is useful to know.
        """
        # Test data
        issued_date = parse_datetime('20180702T184500+0000')
        duration = 90

        # Set up stubs
        stub_issued.return_value = issued_date
        stub_duration.return_value = duration

        expected = issued_date + tdelta(days=90)
        self.assertEqual(self.sut.expiry, expected)

    @mock_property(MarketOrder, 'data')
    def test_issued(self, stub_data):
        """Alias for the data item.

        Timestamps in the data are stored as milliseconds since the
        epoch. The issued property converts these to a UTC datetime.
        """
        # Set up stubs
        stub_data.return_value = {
            'issued': 1529798700000
        }

        self.assertEqual(
            self.sut.issued,
            parse_datetime('20180624000500+0000')
        )

    def test_json__derived_from_data(self):
        """When instantiated with data, JSON is derived."""
        data_dict = {'a': 'fish'}
        sut = MarketOrder(data=data_dict)
        self.assertEqual(sut.json, '{"a": "fish"}')

    def test_json__via_from_json(self):
        """JSON used to instantiate is available as the JSON property.
        """
        json_string = '{"a":  "fish"}'
        sut = MarketOrder.from_json(string=json_string)
        self.assertEqual(sut.json, json_string)

    # ----------------------------------------------------------------
    # Magic Methods
    # ----------------------------------------------------------------
    @mock_property(MarketOrder, 'data')
    def test___getitem__(self, stub_data):
        """MarketOrder provides dict-like access to data."""
        stub_data.return_value = {'a': 'fish'}
        self.assertEqual(self.sut['a'], 'fish')

    # ----------------------------------------------------------------
    # Test nuances in source data (data source dependent)
    #
    # Data may be sourced from the ESI API both raw and deserialised,
    # and other sources such as EveKit and log files.
    # ----------------------------------------------------------------
    @mock_property(MarketOrder, 'data')
    def test_issued__raw_api_json(self, stub_data):
        """Check instantiation with unparsed JSON directly from ESI.

        Types are mostly integers, except for the following items:

            is_buy_order : boolean
            issued : string (date-time)
            price : number (double)
            range : string

        Because the 'issued' field is more complex it is checked
        explicitly here, especially because its type/format can vary
        slightly depending what source it is obtained from.
        """
        stub_data.return_value = {'issued': "2018-05-29T18:22:34Z"}
        self.assertEqual(self.sut.issued,
                         parse_datetime('20180529182234+0000'))

    @mock_property(MarketOrder, 'data')
    def test_issued__pyswagger_dict(self, stub_data):
        """Check behaviour when built from pre-deserialised API data.

        esipy (or technically the underlying pyswagger library)
        returns data with timestamps as custom datetime primitives.
        This is not the most helpful thing, but we expect MarketOrder
        to handle this gracefully by normalising the type in the
        issued property.

        Note that this can be worked around at the interface by
        choosing to receive raw data from the API rather than parsed
        data, which is noted to more performant by the esipy author
        (though at some point it will generally need deserialising).

        This is really dependent on the internals of the pyswagger
        library because of the way it's been implemented, so this test
        acts as a guard in that respect by mocking the primitive. It
        is assumed that the pyswagger Datetime "constructor" creates a
        valid datetime from a source string and assigns it to the `v`
        attribute (current behaviour).
        """
        mock_dt = mock.Mock(
            spec=pyswagger.primitives.Datetime,
            v=parse_datetime("2018-05-29T18:22:34Z"),
        )
        stub_data.return_value = {'issued': mock_dt}

        expected = mock_dt.v

        self.assertIsInstance(self.sut.issued, datetime.datetime)
        self.assertEqual(self.sut.issued, expected)

    @mock_property(MarketOrder, 'data')
    def test_issued__evekit_json(self, stub_data):
        """Check instantiation with unparsed JSON from EveKit.

        EveKit stores datetimes as epoch timestamps so the handling of
        this correctly in the `issued` property is checked here.
        """
        stub_data.return_value = {'issued': 1527614554}
        self.assertEqual(self.sut.issued,
                         parse_datetime('20180529182234'))

    @mock_property(MarketOrder, 'data')
    def test_is_buy_order__raw_api_json__wallet_sell_order(self,
                                                           stub_data):
        """Check the field value is inferred.

        Sell orders from a character wallet don't have the
        is_buy_order field, so it is expected that the class will
        handle this.
        """
        stub_data.return_value = {}
        self.assertFalse(self.sut.is_buy_order)

    @mock_property(MarketOrder, 'data')
    def test__all_implemented_fields__raw_api_json(self, stub_data):
        """Given a native ESI JSON string, checks field properties.

        Properties that do not represent model attribute are not
        checked (e.g.  `json` and `data`)
        """
        with open(os.path.join(DATA_DIR, 'esi_sell_order.json')) as f:
            stub_data.return_value = json.load(f)

        self.assertEqual(self.sut.duration, 90)
        self.assertEqual(self.sut.expiry,
                         parse_datetime('20180919195950+0000'))
        self.assertEqual(self.sut.is_buy_order, False)
        self.assertEqual(self.sut.issued,
                         parse_datetime('20180621195950+0000'))



if __name__ == '__main__':
    unittest.main()
