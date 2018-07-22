import datetime
import functools
import json
import logging
import os
import unittest
from unittest import mock

import ddt
import pyswagger

from .. import place, static, trade
from ..trade import (SimpleMarketOrder, MarketOrderSnapshot,
                     VersionedMarketOrder, TradeItem)
from ..util import parse_datetime, tdelta

from . import DATA_DIR, mock_property


class TestSimpleMarketOrder(unittest.TestCase):
    """Exercise the SimpleMarketOrder class.

    The SimpleMarketOrder class is a wrapper around market order data,
    exposing those data elements that are used elsewhere in the
    codebase. Data describing Market Orders can come from multiple
    sources in multiple formats and differ slightly in its content and
    purpose, so part of the role of the wrapper is to provide a
    standardised API.

    A SimpleMarketOrder is an important, base type this code so some
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
        self.sut = SimpleMarketOrder(data={})

    # ----------------------------------------------------------------
    # Constructors
    # ----------------------------------------------------------------
    def test___init___data(self):
        """Data provided on init is available via the data property.

        The SimpleMarketOrder class doesn't actually care what data is
        provided, just that it is a valid dict. Erroneous data will
        become apparent quickly when trying to make use of it and this
        saves testing it.
        """
        data_dict = {'a': 'fish'}
        sut = SimpleMarketOrder(data=data_dict)
        self.assertEqual(sut.data, data_dict)

    def test_from_json(self):
        """The JSON constructor provides an alternative init path.

        JSON data is implicitly validated (though the content is not!)
        because the constructor creates the data attribute as a
        side-effect (this is tested here).
        """
        json_string = '{"a": "fish"}'
        sut = SimpleMarketOrder.from_json(string=json_string)
        self.assertEqual(sut.data, {'a': 'fish'})

    # ----------------------------------------------------------------
    # Properties
    # ----------------------------------------------------------------
    @mock_property(SimpleMarketOrder, 'issued')
    @mock_property(SimpleMarketOrder, 'duration')
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

    @mock_property(SimpleMarketOrder, 'data')
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
        sut = SimpleMarketOrder(data=data_dict)
        self.assertEqual(sut.json, '{"a": "fish"}')

    def test_json__via_from_json(self):
        """JSON used to instantiate is available as the JSON property.
        """
        json_string = '{"a":  "fish"}'
        sut = SimpleMarketOrder.from_json(string=json_string)
        self.assertEqual(sut.json, json_string)

    @mock.patch.object(place, 'Station')
    def test_location(self, mock_class):
        """Property value is a place.Station instance.

        All orders are issued in a station indicated by the order's
        location_id field. This property enriches that with
        information pulled from static data.
        """
        sut = SimpleMarketOrder(data={'location_id': 1234})
        retval = sut.location
        mock_class.assert_called_with(1234)
        self.assertIs(retval, mock_class.return_value)

    @mock.patch.object(trade, 'TradeItem')
    def test_item(self, mock_class):
        """Property value is a TradeItem instance.

        All orders are associated with a tradeable item type via the
        type_id field. This property enriches that with information
        pulled from static data.
        """
        sut = SimpleMarketOrder(data={'type_id': 34})
        retval = sut.item
        mock_class.assert_called_with(34)
        self.assertIs(retval, mock_class.return_value)

    # ----------------------------------------------------------------
    # Magic Methods
    # ----------------------------------------------------------------
    @mock_property(SimpleMarketOrder, 'data')
    def test___getitem__(self, stub_data):
        """SimpleMarketOrder provides dict-like access to data."""
        stub_data.return_value = {'a': 'fish'}
        self.assertEqual(self.sut['a'], 'fish')

    # ----------------------------------------------------------------
    # Test nuances in source data (data source dependent)
    #
    # Data may be sourced from the ESI API both raw and deserialised,
    # and other sources such as EveKit and log files.
    # ----------------------------------------------------------------
    @mock_property(SimpleMarketOrder, 'data')
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

    @mock_property(SimpleMarketOrder, 'data')
    def test_issued__pyswagger_dict(self, stub_data):
        """Check behaviour when built from pre-deserialised API data.

        esipy (or technically the underlying pyswagger library)
        returns data with timestamps as custom datetime primitives.
        This is not the most helpful thing, but we expect
        SimpleMarketOrder to handle this gracefully by normalising the
        type in the issued property.

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

    @mock_property(SimpleMarketOrder, 'data')
    def test_issued__evekit_json(self, stub_data):
        """Check instantiation with unparsed JSON from EveKit.

        EveKit stores datetimes as epoch timestamps so the handling of
        this correctly in the `issued` property is checked here.
        """
        stub_data.return_value = {'issued': 1527614554}
        self.assertEqual(self.sut.issued,
                         parse_datetime('20180529182234'))

    @mock_property(SimpleMarketOrder, 'data')
    def test_is_buy_order__raw_api_json__wallet_sell_order(self,
                                                           stub_data):
        """Check the field value is inferred.

        Sell orders from a character wallet don't have the
        is_buy_order field, so it is expected that the class will
        handle this.
        """
        stub_data.return_value = {}
        self.assertFalse(self.sut.is_buy_order)

    @mock_property(SimpleMarketOrder, 'data')
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



@ddt.ddt
class TestMarketOrderSnapshot(unittest.TestCase):
    """Exercises the timestamp-annotated market order type."""

    t = parse_datetime('20180705204200+0000')

    @ddt.data(
        [(), {'obj': {}, 't': t}, t, None],
        [(),
         {'obj': mock.Mock(spec=SimpleMarketOrder, data={}), 't': t},
         t,
         None],
        [(), {'obj': {}}, None, TypeError],
    )
    @ddt.unpack
    def test___init__(self, args, kwargs, expected_t, error):
        """init is similar to SimpleMarketOrder but includes time."""
        if error is not None:
            self.assertRaises(error, MarketOrderSnapshot, *args,
                              **kwargs)
        else:
            sut = MarketOrderSnapshot(*args, **kwargs)
            self.assertEqual(sut.t, expected_t)


@ddt.ddt
class TestVersionedMarketOrder(unittest.TestCase):
    """Exercises the market order extension with historical snapshots.
    """

    ts = (
        parse_datetime('20180705215200+0000'),
        parse_datetime('20180705204200+0000'),
        parse_datetime('20180705214200+0000'),
    )

    def setUp(self):
        self.snapshots = [
            mock.Mock(
                spec=MarketOrderSnapshot,
                t=t,
                order_id=1234
            )
            for t in self.ts
        ]
        self.sut = VersionedMarketOrder.from_snapshots(self.snapshots)

    def test_snapshots__count(self):
        """Property should contain all snapshots provided on init."""
        self.assertEqual(len(self.sut.snapshots), 3)

    def test_snapshots__type(self):
        """The snapshots property value should be a dictionary.

        The dict maps ISO datetime strings to MarketOrderSnapshot
        instance.
        """
        self.assertIsInstance(self.sut.snapshots, dict)
        iso_timestamp = '2018-07-05T20:42:00+00:00'
        self.assertIn(iso_timestamp, self.sut.snapshots)
        self.assertIs(self.sut.snapshots[iso_timestamp],
                      self.snapshots[1])

    def test_data(self):
        """The instance's data property is the latest snapshot's.

        The latest snapshot is the one with the latest timestamp.
        """
        self.assertEqual(self.sut.t, self.ts[0])

    @mock_property(VersionedMarketOrder, 'order_id')
    def test_add__dissimilar(self, stub_order_id):
        """Adding a snapshot is only possible for the same order ID.
        """
        stub_order_id.return_value = 1234
        self.assertRaises(
            ValueError,
            self.sut.add,
            mock.Mock(
                spec=MarketOrderSnapshot,
                t=parse_datetime('20180705215300+0000'),
                order_id=4321
            )
        )

    @mock.patch.object(VersionedMarketOrder, '_validate_order_id')
    def test_add__newer(self, mock_validator):
        """Adding a newer snapshot will automatically be reflected.
        """
        snapshot_time = parse_datetime('20180705215300+0000')
        self.sut.add(
            mock.Mock(
                spec=MarketOrderSnapshot,
                t=snapshot_time,
            )
        )
        self.assertEqual(self.sut.t, snapshot_time)

    @mock.patch.object(VersionedMarketOrder, '_validate_order_id')
    @ddt.data(
        # 1. SimpleMarketOrder w/ timestamp is OK
        {'obj': mock.Mock(spec=SimpleMarketOrder), 't': ts[0],
         'error': None},
        # 2. SimpleMarketOrder w/o timestamp is not OK.
        {'obj': mock.Mock(spec=SimpleMarketOrder), 't': None,
         'error': TypeError},
        # 3. MarketOrderSnapshot w/o timestamp is OK
        {'obj': mock.Mock(spec=MarketOrderSnapshot, t=ts[0]),
         't': None, 'error': None},
        # 4. MarketOrderSnapshot w/ matching timestamp is OK
        {'obj': mock.Mock(spec=MarketOrderSnapshot, t=ts[0]),
         't': ts[0], 'error': None},
        # 5. MarketOrderSnapshot w/ inconsistent timestamp is not OK
        {'obj': mock.Mock(spec=MarketOrderSnapshot, t=ts[0]), 't': 2,
         'error': ValueError},
        # 6. Data dict w/ a timestamp is OK
        {'obj': {}, 't': ts[0], 'error': None},
        # 7. Data dict w/o timestamp is not OK
        {'obj': {}, 't': None, 'error': TypeError},
    )
    def test_add(self, kwargs, mock_validator):
        """Method supports adding snapshots as various source types.
        """
        error = kwargs.pop('error')
        if error:
            self.assertRaises(error, self.sut.add, **kwargs)
        else:
            self.sut.add(**kwargs)
        self.assertIn(self.ts[0].isoformat(), self.sut.snapshots)


class TestTradeItem(unittest.TestCase):

    def test_integration__get_metadata__entity_param(self):
        """The correct entity name should be passed on instantiation.
        """
        static.global_esd = mock.Mock(spec=type(static.global_esd))
        static.global_esd.get_metadata.return_value = {}
        TradeItem(-1)
        static.global_esd.get_metadata.assert_called_once_with(
            'market_type',
            -1
        )


if __name__ == '__main__':
    unittest.main()
