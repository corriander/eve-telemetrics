import json

import pyswagger

from . import util, place, static
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
    def id(self):
        """Order ID."""
        return self.data['order_id']

    @property
    def location(self):
        """Location of market order (the station it was issued in)."""
        return place.Station(self['location_id'])

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

    @property
    def item(self):
        """Trade item the market order is for."""
        return TradeItem(self.data['type_id'])

    @util.cached_property
    def json(self):
        """Serialised JSON string for the market order."""
        self._log.debug('Serialising data to json string.')
        return json.dumps(self.data)

    @property
    def order_id(self):
        return self.data['order_id']


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


class VersionedMarketOrder(MarketOrderSnapshot):
    """An extended market order model with a version history."""

    def __init__(self, obj=None, t=None):
        """Optionally initialise a new instance with a market order.

        Any combination of arguments acceptable to `add` is allowed,
        with the addition of omitting both parameters or specifying
        them as null (in which case no snapshots will be present yet).
        """
        if any([obj, t]):
            self.add(obj, t)

    @classmethod
    def from_snapshots(cls, snapshots):
        """Build a VersionedMarketOrder from a sequence of snapshots.
        """
        assert len(set(order.order_id for order in snapshots)) == 1
        snapshot_dict = {o.t.isoformat(): o for o in snapshots}
        inst = cls()
        inst.snapshots = snapshot_dict
        return inst

    @property
    def data(self):
        """The data dict of the latest snapshot/version of this order.
        """
        return self.latest.data

    @property
    def latest(self):
        """The latest snapshot/version of this market order."""
        return sorted(self.snapshots.items())[-1][1]

    @property
    def t(self):
        """Timestamp of latest snapshot/version of this market order.
        """
        return self.latest.t

    def _validate_order_id(self, other):
        # Check that the order ID of other is consistent with self.
        if other.order_id != self.order_id:
            raise ValueError(
                "Order ID of {} is not consistent with this "
                "order ID ({})".format(other, self.order_id)
            )

    def add(self, obj, t=None):
        """Add a snapshot/version to the order history.

        Parameters
        ----------

        obj : SimpleMarketOrder or dict
            Order data, or simpler representation.

        t : datetime.datetime
            Timestamp (if obj is MarketOrderSnapshot it will have one
            already, and if this is provided it must be consistent).
        """
        if isinstance(obj, MarketOrderSnapshot):
            snapshot = obj
            if t is not None and obj.t != t:
                raise ValueError("t provided but different to "
                                 "the provided snapshot's t")
            t = obj.t

        elif isinstance(obj, (SimpleMarketOrder, dict)):
            if t is None:
                raise TypeError("t must be specified if a "
                                "MarketOrderSnapshot isn't provided.")
            snapshot = MarketOrderSnapshot(obj, t)

        else:
            raise TypeError("Unsupported parameter types.")
        self._validate_order_id(snapshot)
        self.snapshots[t.isoformat()] = snapshot


class TradeItem(static.StaticEntity):
    """Simple representation of a tradeable item type."""

    _entity_name = 'market_type'
    _id_field = 'typeID'
    _name_field = 'typeName'
    _table = 'invTypes'
    _cache = {}


