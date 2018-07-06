import json

import pyswagger

from . import util
from . import LoggingObject


class SimpleMarketOrder(LoggingObject):

    def __init__(self, data):
        """Initialise a SimpleMarketOrder from source data.

        Parameters
        ----------

        data : dict
            Data dictionary for the market order. Content is not
            validated; this class trusts that valid data is supplied.
        """
        self.data = data

    @classmethod
    def from_json(cls, string):
        """Create a SimpleMarketOrder from a JSON string.

        JSON is validated, but content is not; this class trusts valid
        market data is supplied. Note that the `json` property will
        not contain re-serialised data, rather it is as supplied.

        If the JSON string supplied cannot successfully be decoded by
        the standard `json` lib, an appropriate exception will be
        raised and the object construction will fail.

        Raises
        ------

        json.JSONDecodeError
        """
        data = json.loads(string)
        inst = cls(data=data)
        inst.json = string
        return inst

    def __getitem__(self, key):
        return self.data[key]

    @util.cached_property
    def data(self):
        """Data dictionary for the market order."""
        self._log.debug('Deserialising json string.')
        return json.loads(self.json)

    @property
    def duration(self):
        """Duration of market order (in days)."""
        return self['duration']

    @property
    def expiry(self):
        """Expiry date and time of market order (in UTC)."""
        return self.issued + util.tdelta(days=self.duration)

    @property
    def is_buy_order(self):
        """Market order is a bid/buy order."""
        return self.data.get('is_buy_order', False)

    @util.cached_property
    def issued(self):
        """Issue date of market order (in UTC)."""
        timestamp = self.data['issued']
        if isinstance(timestamp, pyswagger.primitives.Datetime):
            return timestamp.v
        else:
            try:
                return util.parse_epoch_timestamp(timestamp)
            except ValueError:
                return util.parse_datetime(timestamp)

    @util.cached_property
    def json(self):
        """Serialised JSON string for the market order."""
        self._log.debug('Serialising data to json string.')
        return json.dumps(self.data)


class MarketOrderSnapshot(SimpleMarketOrder):
    """An extended market order model with a timestamp."""

    def __init__(self, obj, t):
        """
        Parameters
        ----------

        obj : dict or SimpleMarketOrder
            Market order data (either in raw, dict form or as a
            SimpleMarketOrder). See SimpleMarketOrder for details
            about the dict.

        t : datetime.datetime
            Timestamp for the snapshot. This is the time the order
            data was collected/viewed/etc.
        """
        if isinstance(obj, SimpleMarketOrder):
            data = obj.data
        else:
            data = obj
        super().__init__(data=data)
        self._t = t

    @property
    def t(self):
        """Timestamp of data snapshot."""
        return self._t
