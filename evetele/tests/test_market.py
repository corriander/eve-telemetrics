import json
import os
import unittest
from unittest import mock

from .. import esi, util, market, trade

from . import DATA_DIR
from .test_esi import ESIClientWrapperTestCase


class TestMarket(ESIClientWrapperTestCase):
    """Exercises the market store.

    The role of Market is as a snapshot cache which provides a method
    for pulling market orders from ESI into `MarketOrderSnapshot`
    objects (annotated with the query time). These are organised by
    location and market type so they can be fetched by other objects.

    A pre-instantiated Market instance is provided in the module for
    re-use but the class can be re-instantiated into separate objects
    if appropriate.
    """
    _sut_class = market.Market

    @classmethod
    def setUpClass(cls):
        with open(os.path.join(DATA_DIR, 'esi_buy_order.json')) as f:
            buy_order = json.load(f)
        with open(os.path.join(DATA_DIR, 'esi_sell_order.json')) as f:
            sell_order = json.load(f)
        cls.order_data_list = [buy_order, sell_order]

    @staticmethod
    def get_type_list(market_obj, region_id, system_id, location_id,
                      type_id):
        region_node = market_obj[region_id]
        system_node = region_node[system_id]
        location_node = system_node[location_id]
        return location_node[type_id]

    @mock.patch.object(util, 'get_utc_datetime')
    def test_update__region_only(self, stub_function):
        """This updates the region's market snapshot for all types.

        Test data includes two types in the same region (10000042), in
        two locations:

          - A buy order for type 40 at location 60005419 in system
            30003411.
          - A sell order for type 506 at location 60005686 in system
            30002053.

        We expect to be able to access these two orders by

            market[region_id][system_id][location_id][type_id]

        and for them to be of type MarketOrderSnapshot, annotated with
        the time of query.
        """
        REGION_ID = 10000042
        NOW = util.parse_datetime('201807160000+0000')

        stub_function.return_value = NOW
        self.sut.fetch.return_value = self.order_data_list
        kwargs = dict(region_id=REGION_ID)

        retval = self.sut.update(**kwargs)

        self.sut.fetch.assert_called_with(
            endpoint='markets_region_id_orders',
            **kwargs
        )

        self.assertIs(retval, self.sut[REGION_ID])

        for order_data in self.order_data_list:
            type_list = self.get_type_list(self.sut, REGION_ID,
                                           order_data['system_id'],
                                           order_data['location_id'],
                                           order_data['type_id'])
            self.assertEqual(len(type_list), 1)

            order = type_list[0]
            self.assertIsInstance(order, trade.MarketOrderSnapshot)
            self.assertEqual(order.t, NOW)
            self.assertEqual(order['order_id'],
                             order_data['order_id'])

    @mock.patch.object(util, 'get_utc_datetime')
    def test_update__region_and_type(self, stub_function):
        """This updates the region's market snapshot for all types.

        Test data includes two types in the same region (10000042), in
        two locations:

          - A buy order for type 40 at location 60005419 in system
            30003411.
          - A sell order for type 506 at location 60005686 in system
            30002053.

        We expect the fetch call to only ask for the type we specify
        (40) and we don't bother checking how the return value is
        processed.
        """
        REGION_ID = 10000042
        TYPE_ID = 40
        NOW = util.parse_datetime('201807160000+0000')

        stub_function.return_value = NOW
        self.sut.fetch.return_value = [self.order_data_list[0]]
        kwargs = dict(region_id=REGION_ID, type_id=TYPE_ID)

        retval = self.sut.update(**kwargs)

        self.sut.fetch.assert_called_with(
            endpoint='markets_region_id_orders',
            **kwargs
        )

    @mock.patch.object(util, 'get_utc_datetime')
    def test_update__replaces_existing_orders(self, stub_function):
        """We expect existing orders to be replaced on further update.

        The Market class is not designed to be an archive.
        """
        REGION_ID = 10000042
        SYSTEM_ID = 30003411
        LOCATION_ID = 60005419
        TYPE_ID = 40

        self.sut.fetch.return_value = [self.order_data_list[0]]
        kwargs = dict(region_id=REGION_ID, type_id=TYPE_ID)

        first_tstamp = util.parse_datetime('201807160000+0000')
        stub_function.return_value = first_tstamp

        def get_type_list():
            return self.get_type_list(self.sut, REGION_ID, SYSTEM_ID,
                                      LOCATION_ID, TYPE_ID)

        self.assertEqual(len(get_type_list()), 0)

        retval = self.sut.update(**kwargs)
        type_list = get_type_list()
        self.assertEqual(len(type_list), 1)
        self.assertEqual(type_list[0].t, first_tstamp)

        second_tstamp = util.parse_datetime('201807260000+0000')
        stub_function.return_value = second_tstamp

        retval = self.sut.update(**kwargs)
        type_list = get_type_list()
        self.assertEqual(len(type_list), 1)
        self.assertEqual(type_list[0].t, second_tstamp)


if __name__ == '__main__':
    unittest.main()
