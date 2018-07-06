import os
import unittest

from .. import local, trade
from . import DATA_DIR


class TestMarketLogFile(unittest.TestCase):
    """MarketLogFile models exported wallet log files."""

    @classmethod
    def setUpClass(cls):
        cls.sut = local.MarketLogFile(os.path.join(
            DATA_DIR,
            'My Orders-2018.07.05 1807.txt'
        ))

    def test___init__path(self):
        """Test that init with a file name works properly.

        Init with a path is implicitly tested in the class setup.
        """
        local.MarketLogFile._DIR = DATA_DIR
        sut = local.MarketLogFile('My Orders-2018.07.05 1807.txt')
        self.assertEqual(len(self.sut.orders), 2)

    def test_orders__len(self):
        """Ensure both orders in the sample log are picked up."""
        self.assertEqual(len(self.sut.orders), 2)

    def test_orders__type(self):
        """Ensure both orders are stored as SimpleMarketOrder instances."""
        self.assertIsInstance(self.sut.orders[0], trade.SimpleMarketOrder)
        self.assertIsInstance(self.sut.orders[1], trade.SimpleMarketOrder)

    def test_orders__metadata_fields(self):
        """Ensure fields are parsed correctly."""
        order = self.sut.orders[0]
        self.assertIn('issued', order.data.keys())       # specified
        self.assertIn('region_id', order.data.keys())    # auto cast
        self.assertIn('system_id', order.data.keys())    # specified
        self.assertIn('location_id', order.data.keys())  # specified
        self.assertIn('is_buy_order', order.data.keys()) # specified
        self.assertIn('char_id', order.data.keys())      # auto cast

    def test_orders__metadata_typecasting(self):
        """Ensure parsed metadata values are cast correctly."""
        order = self.sut.orders[0]
        self.assertEqual(order.data['issued'],
                         '2018-06-29 18:22:34.000Z') # TZ appended
        self.assertIsInstance(order.data['system_id'], int)
        self.assertIsInstance(order.data['order_id'], int)
        self.assertIsInstance(order.data['is_buy_order'], bool)


if __name__ == '__main__':
    unittest.main()
