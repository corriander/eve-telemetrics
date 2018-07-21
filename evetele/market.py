"""Market models."""
import collections
import itertools

from . import esi, util, trade
from . import LoggingObject, config


class Market(esi.ESIClientWrapper):
    """A cache for market orders organised by location and type.

    It is the responsibility of data consumers to update this cache as
    required and work with the data in the format provided by an ESI
    client as appropriate.

    Note that if you want to re-use a single market, there a
    pre-instantiated market provided by this module that uses a
    default client instance.
    """

    _client_class = esi.ESIClient

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # region_id: regional market data
        self._data = collections.defaultdict(
            # system_id: system market data
            lambda: collections.defaultdict(
                # location_id: location market data
                lambda: collections.defaultdict(
                    # type_id: market orders
                    lambda: collections.defaultdict(list)
                )
            )
        )

    def __getitem__(self, key):
        return self._data[key]

    def update(self, region_id, type_id=None):
        """Update the market data dict and return the updated subset.

        If `type_id` is not specified, the entire regional market will
        be updated, otherwise only orders for that market type will be
        updated. The update is always region-wide and for either all
        types or a single type because this is the degree of freedom
        offered by the ESI API.
        """
        tstamp = util.get_utc_datetime()
        endpoint = 'markets_region_id_orders'
        params = {'region_id': region_id}
        if type_id is not None:
            params.update({'type_id': type_id})

        region_node = self._data[region_id]
        seen = set()
        for data in self.fetch(endpoint=endpoint, **params):
            type_id = data['type_id']
            system_node = region_node[data['system_id']]
            station_node = system_node[data['location_id']]
            order_list = station_node[type_id]
            if not type_id in seen:
                # Remove the contents of the current order list
                del order_list[:]
                seen.add(type_id)
            order_list.append(
                trade.MarketOrderSnapshot(data, t=tstamp)
            )
        return region_node


market = Market()
