import json
import os
import unittest
from unittest import mock

from .. import character, trade

from . import DATA_DIR
from .test_esi import ESIClientWrapperTestCase


class TestCharacter(ESIClientWrapperTestCase):

    _sut_class = character.Character

    @property
    def sample_api_info(self):
        try:
            return self._sample_api_info
        except AttributeError:
            with open(os.path.join(DATA_DIR, 'api_info.json')) as f:
                self._sample_api_info = json.load(f)
            return self._sample_api_info

    def test_name(self):
        """The character name is resolved from the security object."""
        self.assertEqual(self.sut.name,
                         self.sample_api_info['CharacterName'])

    def test_id(self):
        """The character ID is resolved from the security object."""
        self.assertEqual(self.sut.id,
                         self.sample_api_info['CharacterID'])

    def test_historic_orders(self):
        """A list of `SimpleMarketOrder` is built from an endpoint.

        The endpoint is 'characters_character_id_orders_history'.
        Unlike open orders, historic (expired/cancelled) orders are
        static and it therefore makes no sense to annotate them with
        time viewed.
        """
        self.sut.fetch.return_value = [{}, {}]

        retval = self.sut.historic_orders()

        # Check the fetch call is made properly
        self.sut.fetch.assert_called_with(
            endpoint='characters_character_id_orders_history',
            character_id=self.sut.id
        )

        # We expect two SimpleMarketOrder objects to be returned.
        self.assertIsInstance(retval, list)
        self.assertEqual(len(retval), 2)
        self.assertIsInstance(retval[0], trade.SimpleMarketOrder)
        self.assertIsInstance(retval[1], trade.SimpleMarketOrder)

    @mock.patch.object(character.util, 'get_utc_datetime')
    def test_open_orders(self, stub_now):
        """A list of `MarketOrderSnapshot` is built from an endpoint.

        The endpoint queried is 'characters_character_id_orders' and
        the time of the query is used to annotate the orders.
        """
        stub_now.return_value = '201807210000'
        self.sut.fetch.return_value = [{}, {}]

        retval = self.sut.open_orders()

        # Check the fetch call is made properly
        self.sut.fetch.assert_called_with(
            endpoint='characters_character_id_orders',
            character_id=self.sut.id
        )

        # We expect two MarketOrderSnapshot objects to be returned.
        self.assertIsInstance(retval, list)
        self.assertEqual(len(retval), 2)
        self.assertIsInstance(retval[0], trade.MarketOrderSnapshot)
        self.assertIsInstance(retval[1], trade.MarketOrderSnapshot)


if __name__ == '__main__':
    unittest.main()
