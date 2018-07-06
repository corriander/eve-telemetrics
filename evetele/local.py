import csv
import ast
import os
from decimal import Decimal


from . import config, trade, util, LoggingObject


class MarketLogFile(LoggingObject):
    """Model of a market log file exported from the client.

    Orders within the log file are accessible via the `orders`
    property.
    """

    _DIR = os.path.expanduser(os.path.join(
        config.get('ClientData', 'root directory'),
        'logs',
        'Marketlogs'
    ))

    _FIELD_MAPPING = {
        'bid': {
            'name': 'is_buy_order',
            'cast': ast.literal_eval
        },
        'issueDate': {
            'name': 'issued',
            'cast': lambda s: s + 'Z' # Specify UTC
        },
        'price': {'cast': Decimal},
        'regionID': {'cast': int},
        'solarSystemID': {
            'name': 'system_id',
            'cast': int
        },
        'stationID': {
            'name': 'location_id',
            'cast': int
        },
        'typeID': {'cast': int},
    }

    def __init__(self, filename=None, path=None):
        """Initialise with either a file name or path.

        Parameters
        ----------

        filename : str, optional
            Filename (e.g. 'My Orders-2018-07-05 1801.txt'). The path
            will be constructed base on the 'root directory' option in
            the 'ClientData' section of config (default location is
            '~/Documents/EVE/logs/Marketlogs').

        path : str, optional
            Full path to log file. Takes precedence over filename.
        """
        if path is None:
            path = os.path.join(self._DIR, filename)

        field_mapping = self._FIELD_MAPPING
        self._orders = orders = []
        with open(path, 'r') as f:
            reader = csv.DictReader(f)
            for record in reader:
                data = {}
                for field, value in record.items():
                    mapping = field_mapping.get(field, {})
                    transformed_name = mapping.get(
                        'name',
                        util.camelcase_to_snakecase(field)
                    )
                    cast = mapping.get('cast', lambda v: v)
                    data[transformed_name] = cast(value)
                orders.append(trade.SimpleMarketOrder(data))

    @property
    def orders(self):
        """Market orders present in the log file."""
        return self._orders
